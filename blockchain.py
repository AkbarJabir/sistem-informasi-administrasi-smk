"""
Blockchain simulation module for Sistem Informasi Administrasi SMK.
In-memory blockchain with SQLite persistence.
Simulates smart contract behavior: issueCertificate, verifyCertificate, revokeCertificate.
"""

import hashlib
import json
import time
import uuid
from datetime import datetime


class Block:
    """Represents a single block in the simulated blockchain."""

    def __init__(self, index, document_hash, document_type, issuer, previous_hash, timestamp=None, tx_hash=None):
        self.index = index
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.document_hash = document_hash
        self.document_type = document_type
        self.issuer = issuer
        self.previous_hash = previous_hash
        self.tx_hash = tx_hash or self._generate_tx_hash()
        self.hash = self._calculate_hash()

    def _calculate_hash(self):
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'document_hash': self.document_hash,
            'document_type': self.document_type,
            'issuer': self.issuer,
            'previous_hash': self.previous_hash,
            'tx_hash': self.tx_hash
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def _generate_tx_hash(self):
        unique_data = f"{self.index}{self.timestamp}{self.document_hash}{uuid.uuid4()}"
        return '0x' + hashlib.sha256(unique_data.encode()).hexdigest()

    def to_dict(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'document_hash': self.document_hash,
            'document_type': self.document_type,
            'issuer': self.issuer,
            'previous_hash': self.previous_hash,
            'tx_hash': self.tx_hash,
            'hash': self.hash
        }


class SmartContract:
    """
    Simulates a smart contract with authorization checks.
    Only authorized issuers can call issueCertificate().
    Includes reentrancy protection.
    """

    AUTHORIZED_ROLES = ['staf_tu', 'kepala_sekolah']

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self._locked = False  # Reentrancy guard

    def _reentrancy_guard(self):
        if self._locked:
            return {
                'success': False,
                'error': 'Transaction Reverted: Reentrancy detected'
            }
        return None

    def issue_certificate(self, issuer_role, issuer_name, document_hash, document_type='ijazah'):
        """
        Issue a certificate by recording its hash on the blockchain.
        Only authorized roles can issue.
        """
        # Reentrancy check
        guard = self._reentrancy_guard()
        if guard:
            return guard

        self._locked = True
        try:
            # Authorization check
            if issuer_role not in self.AUTHORIZED_ROLES:
                return {
                    'success': False,
                    'error': 'Transaction Reverted: Unauthorized. '
                             f'Role "{issuer_role}" is not authorized to issue certificates.'
                }

            # Check for duplicate hash
            existing = self.blockchain.find_by_document_hash(document_hash)
            if existing:
                return {
                    'success': False,
                    'error': 'Transaction Reverted: Document hash already exists on blockchain.'
                }

            # Add block to chain
            block = self.blockchain.add_block(document_hash, document_type, issuer_name)
            return {
                'success': True,
                'tx_hash': block.tx_hash,
                'block_index': block.index,
                'block_hash': block.hash,
                'message': f'Certificate issued successfully. Block #{block.index}'
            }
        finally:
            self._locked = False

    def verify_certificate(self, document_hash):
        """
        Verify a certificate by looking up its hash on the blockchain.
        Returns verification result.
        """
        record = self.blockchain.find_by_document_hash(document_hash)
        if record:
            return {
                'verified': True,
                'status': 'VALID',
                'message': 'AUTHENTIC DOCUMENT — Hash matches blockchain record.',
                'block_index': record['index'],
                'tx_hash': record['tx_hash'],
                'issued_at': record['timestamp'],
                'issuer': record['issuer'],
                'document_type': record['document_type']
            }
        else:
            return {
                'verified': False,
                'status': 'INVALID',
                'message': 'FALSIFIED DOCUMENT — Hash does not match any blockchain record.',
                'block_index': None,
                'tx_hash': None
            }

    def revoke_certificate(self, issuer_role, issuer_name, document_hash):
        """Revoke a certificate (authorized only)."""
        guard = self._reentrancy_guard()
        if guard:
            return guard

        self._locked = True
        try:
            if issuer_role not in self.AUTHORIZED_ROLES:
                return {
                    'success': False,
                    'error': 'Transaction Reverted: Unauthorized'
                }

            record = self.blockchain.find_by_document_hash(document_hash)
            if not record:
                return {
                    'success': False,
                    'error': 'Transaction Reverted: Document hash not found'
                }

            # Record revocation as a new block
            revoke_hash = hashlib.sha256(f"REVOKED:{document_hash}".encode()).hexdigest()
            block = self.blockchain.add_block(revoke_hash, 'revocation', issuer_name)
            return {
                'success': True,
                'tx_hash': block.tx_hash,
                'message': f'Certificate revoked. Revocation block #{block.index}'
            }
        finally:
            self._locked = False


class Blockchain:
    """
    In-memory blockchain simulation with hash chaining.
    Persisted to SQLite via database module.
    """

    def __init__(self):
        self.chain = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0,
            document_hash='0' * 64,
            document_type='genesis',
            issuer='SYSTEM',
            previous_hash='0' * 64,
            timestamp='2024-01-01T00:00:00',
            tx_hash='0x0000000000000000000000000000000000000000000000000000000000000000'
        )
        self.chain.append(genesis)

    def add_block(self, document_hash, document_type, issuer):
        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            document_hash=document_hash,
            document_type=document_type,
            issuer=issuer,
            previous_hash=previous_block.hash
        )
        self.chain.append(new_block)

        # Persist to SQLite
        self._persist_block(new_block)
        return new_block

    def find_by_document_hash(self, document_hash):
        """Search chain for a document hash."""
        for block in reversed(self.chain):
            if block.document_hash == document_hash:
                return block.to_dict()
        return None

    def verify_chain_integrity(self):
        """Verify the integrity of the entire chain."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.previous_hash != previous.hash:
                return False, f"Chain broken at block {i}"
            recalculated = current._calculate_hash()
            if current.hash != recalculated:
                return False, f"Hash mismatch at block {i}"
        return True, "Chain integrity verified"

    def get_chain_info(self):
        """Get chain statistics."""
        return {
            'length': len(self.chain),
            'latest_block': self.chain[-1].to_dict() if self.chain else None,
            'integrity': self.verify_chain_integrity()
        }

    def get_all_blocks(self):
        """Return all blocks as dicts."""
        return [block.to_dict() for block in self.chain]

    def _persist_block(self, block):
        """Persist block to SQLite database."""
        try:
            from database import get_db
            db = get_db()
            db.execute(
                """INSERT INTO blockchain_records
                (block_index, previous_hash, document_hash, document_type, timestamp, issuer, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (block.index, block.previous_hash, block.document_hash,
                 block.document_type, block.timestamp, block.issuer, block.tx_hash)
            )
            db.commit()
            db.close()
        except Exception:
            pass  # Silently fail persistence for prototype

    def load_from_db(self):
        """Load existing blockchain records from database."""
        try:
            from database import get_db
            db = get_db()
            records = db.execute(
                "SELECT * FROM blockchain_records ORDER BY block_index ASC"
            ).fetchall()
            db.close()

            if records:
                self.chain = []
                self._create_genesis_block()
                for record in records:
                    block = Block(
                        index=record['block_index'],
                        document_hash=record['document_hash'],
                        document_type=record['document_type'],
                        issuer=record['issuer'],
                        previous_hash=record['previous_hash'],
                        timestamp=record['timestamp'],
                        tx_hash=record['tx_hash']
                    )
                    self.chain.append(block)
        except Exception:
            pass


# ── Global instances ──
blockchain = Blockchain()
blockchain.load_from_db()
smart_contract = SmartContract(blockchain)


def compute_sha256(data):
    """Compute SHA-256 hash of bytes data."""
    return hashlib.sha256(data).hexdigest()
