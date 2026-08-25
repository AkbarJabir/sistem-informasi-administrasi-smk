# Sistem Informasi Administrasi SMK

Prototype Sistem Informasi Administrasi SMK dengan pendekatan **Zero Trust Architecture** dan **Blockchain Simulation** untuk meningkatkan keamanan akses serta integritas dokumen administrasi sekolah.

## 📌 Deskripsi

Sistem ini merupakan prototype Sistem Informasi Administrasi SMK yang dirancang untuk mengelola data siswa, nilai, ijazah, sertifikat PKL, serta proses administrasi terkait.

Fokus utama proyek adalah penerapan konsep keamanan pada aplikasi melalui:

- Role-Based Access Control (RBAC)
- Multi-Factor Authentication (MFA)
- Zero Trust Policy Enforcement
- Audit Logging
- Blockchain Simulation
- SHA-256 Document Hashing
- Document Verification
- Security Operations Dashboard
- Cloud Security Architecture Design

> **Catatan:** Prototype ini berjalan secara lokal. Komponen cloud seperti WAF, DDoS Protection, VPC, Cloud KMS/HSM, dan enkripsi cloud merupakan bagian dari rancangan arsitektur keamanan dan belum diterapkan sebagai infrastruktur cloud produksi. Blockchain yang digunakan pada prototype juga masih berupa simulasi.

---

## 🎯 Tujuan Proyek

Proyek ini bertujuan untuk:

1. Merancang keamanan Sistem Informasi Administrasi SMK menggunakan prinsip Zero Trust.
2. Membatasi akses pengguna berdasarkan identitas dan perannya.
3. Menambahkan MFA untuk akun administratif.
4. Mencatat aktivitas penting melalui audit log.
5. Menjaga integritas dokumen administrasi menggunakan SHA-256 dan blockchain simulation.
6. Menyediakan mekanisme verifikasi dokumen untuk mengetahui apakah dokumen telah mengalami perubahan.
7. Menjadi prototype untuk mendukung perancangan Cloud Security Architecture.

---

## 👥 User Roles

| Role | Fungsi Utama |
|---|---|
| Siswa | Melihat data dan nilai sendiri |
| Guru | Mengelola nilai siswa |
| Staf TU | Mengelola administrasi dan membuat dokumen |
| Kepala Sekolah | Menyetujui penerbitan ijazah |
| Mitra DUDI | Melakukan verifikasi dokumen |

Akses setiap role dibatasi menggunakan mekanisme **RBAC** pada backend.

---

## 🔐 Security Features

### Zero Trust & Access Control

- Authentication
- Role-Based Access Control (RBAC)
- Backend authorization
- 403 Forbidden untuk akses yang tidak diizinkan
- Session-based identity verification
- MFA untuk akun administratif

### Audit & Monitoring

- Audit log aktivitas pengguna
- Pencatatan perubahan nilai
- Pencatatan akses yang ditolak
- Security Operations Dashboard

### Blockchain Simulation

Prototype menyediakan simulasi blockchain untuk:

- Penyimpanan hash dokumen
- Hash chaining
- SHA-256
- Pencatatan metadata dokumen
- Otorisasi penerbitan
- Verifikasi integritas dokumen

### Document Verification

Dokumen dapat diverifikasi menggunakan hash SHA-256.

```text
Dokumen
   ↓
SHA-256
   ↓
Hash Dokumen
   ↓
Blockchain Record
   ↓
Verifikasi
