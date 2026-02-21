# Phase 14 Research: Application-Level Data Reduction & DRR Variants

## Problem Statement

Dell PowerStore publishes DRR benchmarks assuming **reducible data** — data that has
not already been compressed, deduplicated, or encrypted by the application layer.
When an application performs any of these operations before data reaches the array,
PowerStore's inline dedup/compression achieves significantly lower ratios than the
published baseline.

**Risk:** Using Oracle's baseline DRR=5.0 on a TDE-enabled Oracle deployment can
**5× under-provision** storage — a critical pre-sales sizing error.

Dell's own documentation formalises this: encrypted data is classified as
"unreducible" and skipped by PowerStore's reduction engine
([KB000267460](https://www.dell.com/support/kbdoc/en-us/000267460)).

---

## Three Families of Application-Level Reduction

### 1. Application Compression

Application compression eliminates the block-level redundancy that PowerStore's
dedup/compression targets. Data arrives at the array already reduced.

#### Oracle Advanced Compression / HCC

Oracle Hybrid Columnar Compression (HCC) reorganises data into columnar format at
10:1–50:1 ratios on eligible data. Dell's PowerStore Oracle best practices confirm
this reduces array-level DRR effectiveness because intra-block redundancy has already
been removed.

- Caveat: DML operations (UPDATE/DELETE) force HCC segment decompression, causing
  data to **expand** back to uncompressed size.
- Sources: [Dell PowerStore Oracle BP](https://infohub.delltechnologies.com/en-ca/l/oracle-rac-high-availability-on-powerstore-t/powerstore-data-efficiencies/) · [HCC DML pitfalls](https://blog.sqlora.com/en/when-compression-expands-the-hidden-pitfalls-of-hcc/)

**Expected DRR impact:** 5.0 → **2.5**

#### SQL Server Page Compression

SQL Server page compression uses prefix and dictionary methods — the same technique
storage arrays use for deduplication. When active, 40–60% of redundancy is eliminated
before PowerStore sees the data.

- Sources: [Microsoft Docs](https://learn.microsoft.com/en-us/sql/relational-databases/data-compression/data-compression?view=sql-server-ver17) · [NetApp SQL Server storage guide](https://docs.netapp.com/us-en/ontap-apps-dbs/mssql/mssql-storage-efficiency.html)

**Expected DRR impact:** 5.0 → **2.5**

#### MongoDB WiredTiger

MongoDB WiredTiger compresses live data with snappy/zstd/zlib, achieving 40–50%
storage reduction before write to disk. Data arriving at PowerStore is already
compressed.

- Source: [Percona WiredTiger compression benchmark](https://www.percona.com/blog/compression-methods-in-mongodb-snappy-vs-zstd/)

**Expected DRR impact:** 1.5 → **1.5** (marginal further reduction possible on
metadata; existing base DRR already reflects this)

> **Note:** PostgreSQL does NOT compress live data (only backups via pg_dump), so
> its base DRR=1.5 remains valid for unencrypted deployments.

---

### 2. Encryption

Encryption randomises data bitstreams, making blocks both incompressible and appearing
unique — completely defeating both compression and deduplication.

**Dell's official position:**
> "Host-encrypted data and application-level encryption such as TDE are classified as
> unreducible data and cannot benefit from compression or deduplication."
> — [KB000267460](https://www.dell.com/support/kbdoc/en-us/000267460)

**Real-world case (PowerMax + Oracle TDE):**
> After enabling TDE, an Oracle database grew back to 1.35 TB (original uncompressed
> size) with no deduplication benefit.
> — [Dell PowerMax Oracle deployment guide](https://infohub.delltechnologies.com/l/deployment-best-practices-for-oracle-databases-with-dell-emc-powermax-5/compression-and-deduplication-of-an-encrypted-oracle-database-5/)

| Application | Encryption Feature | Expected DRR |
|---|---|---|
| Oracle | TDE (Transparent Data Encryption) | 1.5 |
| SQL Server | TDE | 1.5 |
| MongoDB | Encrypted Storage Engine | 1.3 |
| PostgreSQL | pgcrypto / tablespace encryption | 1.3 |
| MySQL / NoSQL | InnoDB encryption | 1.3 |
| Kubernetes | Encrypted PVs (LUKS/CSI) | 1.3 |

A DRR of 1.5 (not 1.0) is used for Oracle/SQL TDE because minor savings from block
alignment and metadata deduplication remain possible even on encrypted data. More
deeply encrypted workloads (MongoDB, Kubernetes) use 1.3 as the conservative floor.

---

### 3. Backup Agent Source-Side Deduplication

When backup agents apply compression and deduplication **before** sending data to the
backup target on PowerStore, the array's data reduction opportunities are exhausted.

#### Veeam

By default, Veeam uses "Optimal" compression at the source DataMover. The Veeam Best
Practices guide explicitly states that deduplication appliances require Veeam
compression to be set to "Auto" or disabled to retain their own dedup effectiveness.

- Sources: [Veeam BP — deduplication repositories](https://bp.veeam.com/vbr/3_Build_structures/B_Veeam_Components/B_backup_repositories/deduplication.html)

**Expected DRR impact:** 1.5 → **1.2**

#### Data Domain Virtual Edition (DDVE)

DDVE is a Dell EMC backup appliance that performs **inline deduplication and
compression** before writing to its datastore on PowerStore. Data stored by DDVE on
the array is already maximally reduced and appears as incompressible, unique blocks.
PowerStore's own dedup/compression engine cannot achieve any further reduction.

**Expected DRR:** **1.0** (1:1 — no additional reduction)

---

## Combined Scenarios

| Scenario | Base DRR | Effective DRR |
|---|---|---|
| Oracle HCC (App Compressed) only | 5.0 | 2.5 |
| Oracle TDE only | 5.0 | 1.5 |
| Oracle HCC + TDE | 5.0 | 1.2 |
| SQL Server Page Compression only | 5.0 | 2.5 |
| SQL Server TDE only | 5.0 | 1.5 |
| SQL Server Page Compression + TDE | 5.0 | 1.2 |
| MongoDB Encrypted | 1.5 | 1.3 |
| PostgreSQL Encrypted | 1.5 | 1.3 |
| MySQL / NoSQL Encrypted | 1.5–5.0 | 1.3 |
| Kubernetes Encrypted PVs | 2.0 | 1.3 |
| Veeam (Compression + Dedup enabled) | 1.5 | 1.2 |
| Commvault (Compression + Dedup enabled) | 1.5 | 1.2 |
| Data Domain Virtual Edition (DDVE) | — | 1.0 |

---

## Implementation in StorePredict

All scenarios above were added as **new subcategory rows in DRR.csv** (42 entries
total, up from 28). The `(category, subcategory) → DRR` lookup architecture required
no code changes — only new CSV rows and companion classifier rules.

Classifier rules at priorities 88–97 detect common naming patterns:

| Pattern example | Classified as |
|---|---|
| `PROD-ORACLE-TDE-01` | Oracle - TDE (Encrypted) |
| `PROD-ORACLE-HCC-TDE-01` | Oracle - HCC + TDE |
| `SQL-PAGE-DB-01` | Microsoft SQL - Page Compressed |
| `MONGO-ENC-01` | MongoDB - Encrypted |
| `DDVE-PROD-01` | Data Domain Virtual Edition (DDVE) |
| `BACKUP-COMMVAULT-01` | Commvault |

Pre-sales engineers can also manually select any variant from the workload dropdown
on the review page for VMs whose names do not follow these conventions.

See ADR-053 for the architectural decision behind the CSV-variant approach.

---

## References

| Source | URL |
|---|---|
| Dell PowerStore KB — DRR less than expected | <https://www.dell.com/support/kbdoc/en-us/000267460> |
| Dell PowerStore 5:1 DRR guarantee | <https://www.delltechnologies.com/asset/en-us/products/cross-company/industry-market/principled-technologies-dell-powerstore-data-reduction-ratio-vs-5-competitors.pdf> |
| Oracle TDE on PowerMax — real-world case | <https://infohub.delltechnologies.com/l/deployment-best-practices-for-oracle-databases-with-dell-emc-powermax-5/compression-and-deduplication-of-an-encrypted-oracle-database-5/> |
| Oracle HCC — PowerStore RAC BP | <https://infohub.delltechnologies.com/en-ca/l/oracle-rac-high-availability-on-powerstore-t/powerstore-data-efficiencies/> |
| Oracle HCC DML pitfalls | <https://blog.sqlora.com/en/when-compression-expands-the-hidden-pitfalls-of-hcc/> |
| SQL Server data compression | <https://learn.microsoft.com/en-us/sql/relational-databases/data-compression/data-compression?view=sql-server-ver17> |
| SQL Server storage efficiency (NetApp) | <https://docs.netapp.com/us-en/ontap-apps-dbs/mssql/mssql-storage-efficiency.html> |
| MongoDB WiredTiger compression benchmark | <https://www.percona.com/blog/compression-methods-in-mongodb-snappy-vs-zstd/> |
| Veeam BP — deduplication appliances | <https://bp.veeam.com/vbr/3_Build_structures/B_Veeam_Components/B_backup_repositories/deduplication.html> |
