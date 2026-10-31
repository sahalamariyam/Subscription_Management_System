# Brightloop Subscription Management System

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0%20Community-purple.svg)](https://www.odoo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker%20Compose-v2%2B-2496ED.svg)](https://www.docker.com/)

A comprehensive Subscription Management System designed to automate subscription lifecycles, plan management, recurring billing, invoice generation, payment tracking, discounts, and revenue analytics through a unified platform.

Central platform repository for the Brightloop Subscription Management System, developed for the Odoo Hackathon.

---

## 1. Architecture & Team Ownership

The project follows an Odoo-native modular monolith architecture divided across four coordinated developer modules:

| Module | Primary Owner | Scope & Responsibility |
| :--- | :--- | :--- |
| `brightloop_core` | **Member 1 (Integration Lead)** | Platform foundation, authentication, security, user/customer management, and shared architecture contracts. |
| `brightloop_subscription` | **Member 2** | Products, variants, subscription plans, quotations, and subscription lifecycle. |
| `brightloop_billing` | **Member 3** | Recurring billing engine, invoices, taxes, discounts, and billing reliability. |
| `brightloop_finance` | **Member 4** | Payments, financial dashboards, reporting, and Excel export. |

---

## 2. Technology Stack & Versions

- **Odoo:** `18.0 Community` (Official Docker image: `odoo:18.0`)
- **Database:** `PostgreSQL 16` (Official Docker image: `postgres:16`)
- **Orchestration:** `Docker Compose`
- **Host Target:** macOS (Apple Silicon arm64 / Intel x86_64) and Linux

---

## 3. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Git](https://git-scm.com/) installed.

---

## 4. Setup & Quick Start Instructions

### Step 1: Environment Configuration
Copy the sample environment file to create your local `.env`:
```bash
cp .env.example .env
```
*(Optionally adjust passwords or ports inside `.env`. Note: `.env` is ignored by Git and should never be committed.)*

### Step 2: Start Services
Launch the PostgreSQL and Odoo services using Docker Compose:
```bash
docker compose up -d
```

### Step 3: Verify Container Health
```bash
docker compose ps
```
Both the `db` service (PostgreSQL 16) and `web` service (Odoo 18) should display state `healthy` / `running`.

### Step 4: Access Odoo
Open your web browser and navigate to:
```
http://localhost:8069
```
On initial boot, create your database (e.g. `brightloop_db`) using the master password configured in `.env` (default: `brightloop_dev_admin_password`).

---

## 5. Addon Development & Installation

The `./addons` directory is automatically mounted into `/mnt/extra-addons` inside the Odoo container.

To install or update the `brightloop_core` addon directly from CLI:
```bash
docker compose exec web odoo -d brightloop_db -i brightloop_core --stop-after-init
```

To run unit tests for `brightloop_core`:
```bash
docker compose exec web odoo -d brightloop_db --test-enable -i brightloop_core --stop-after-init
```

---

## 6. Environment Management Commands

* **View Logs:**
  ```bash
  docker compose logs -f web
  ```
* **Stop Environment:**
  ```bash
  docker compose stop
  ```
* **Restart Environment:**
  ```bash
  docker compose restart
  ```
* **Tear Down (Preserving Data Volumes):**
  ```bash
  docker compose down
  ```
* **Tear Down and Clear Volumes (Data Reset):**
  ```bash
  docker compose down -v
  ```
