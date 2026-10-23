# 🏨 Hôtel – Gestion et réservation de chambres

Application web full-stack : **React (Vite) → API REST (JWT) → Django REST Framework → PostgreSQL**.
Le frontend n'accède jamais à la base ; toutes les règles (prix, dates, disponibilités) sont recalculées côté serveur.

## Technologies
Python 3.11+ · Django 5.1/5.2 · DRF · SimpleJWT · django-filter · drf-spectacular (Swagger) · ReportLab (factures PDF) ·
**PostgreSQL 14+** (psycopg 3) · React 18 · React Router · Axios · Bootstrap 5 · Recharts · React-Toastify

## Installation

### 1. PostgreSQL
**Option A – Docker** (le plus simple) : `docker compose up -d` (utilise `docker-compose.yml`, base `hotel_db`, utilisateur `hotel_user`, mot de passe `change-me`).

**Option B – PostgreSQL installé** :
```bash
sudo -u postgres psql
CREATE USER hotel_user WITH PASSWORD 'VotreMotDePasse' CREATEDB;   -- CREATEDB : nécessaire pour lancer les tests
CREATE DATABASE hotel_db OWNER hotel_user ENCODING 'UTF8';
\q
```
> L'extension `btree_gist` (anti double réservation) est créée automatiquement par la migration. Elle est « de confiance »
> depuis PostgreSQL 13 : le propriétaire de la base suffit. Avant PostgreSQL 13, exécutez une fois en superutilisateur :
> `psql -d hotel_db -c "CREATE EXTENSION btree_gist;"`.

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # puis éditez SECRET_KEY et DB_PASSWORD
python manage.py migrate
python manage.py seed_demo          # comptes + chambres + services de démonstration (facultatif)
python manage.py runserver          # http://localhost:8000   —   Swagger : /api/docs/
```
Générer une clé secrète : `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`.

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env                # VITE_API_URL=http://localhost:8000/api
npm run dev                         # http://localhost:5173
```

## Comptes de démonstration (après `seed_demo` — à supprimer en production)
| Rôle | E-mail | Mot de passe |
|---|---|---|
| Administrateur | admin@hotel.com | Admin123! |
| Réceptionniste | reception@hotel.com | Reception123! |
| Client | client@hotel.com | Client123! |

## Règles métier
- **Prix minimum : 20 000 Ar par nuit** et par chambre (constante `apps/common/constants.py`, validateurs, contrainte SQL `chk_prix`).
- **Total** = prix_nuit × nuits + services − réduction long séjour + taxes ; un seul moteur : `apps/reservations/pricing.py`.
  Le serveur ignore et refuse tout montant envoyé par le client ; le prix est relu en base sous verrou puis figé dans la réservation.
- **Pas de double réservation** (3 niveaux) : contrôle applicatif → verrou `SELECT … FOR UPDATE` sur la chambre →
  **contrainte d'exclusion PostgreSQL** `excl_resa_chevauchement` (rempart final, même si le code est contourné).
  Départ et arrivée le même jour sont autorisés. Un conflit renvoie **HTTP 409**.
- **Fuseau horaire** : `Indian/Antananarivo` (UTC+3) ; « aujourd'hui » et le délai d'annulation suivent l'heure de l'hôtel.
- Annulation par le client jusqu'à 48 h avant l'arrivée (`CANCEL_DEADLINE_HOURS`) ; le personnel peut toujours annuler.
- Facture : réservation confirmée ou terminée uniquement, une par réservation.
- **Paiements** : espèces et virement sont enregistrés par la réception uniquement. Carte / Mobile Money passent par
  `apps/paiements/providers.py` ; tant qu'aucun vrai fournisseur n'est branché, le paiement en ligne est **refusé**
  (`PAIEMENT_SIMULE=False`). `PAIEMENT_SIMULE=True` (développement) accepte tout — ne jamais l'activer en production.

## API (extraits)
| Méthode | Endpoint |
|---|---|
| POST | `/api/auth/register/` · `/login/` · `/refresh/` · `/logout/` · `/change-password/` ; GET/PATCH `/api/auth/me/` |
| CRUD | `/api/chambres/` · `/clients/` · `/reservations/` · `/services/` · `/categories/` · `/equipements/` · `/users/` |
| GET | `/api/chambres/disponibles/?arrivee=&depart=&categorie=&personnes=` |
| POST | `/api/reservations/devis/` (simulation de prix) · `/{id}/annuler/` · `confirmer/` · `checkin/` · `checkout/` |
| GET/POST | `/api/paiements/` ; POST `/api/paiements/{id}/rembourser/` |
| GET/POST | `/api/factures/` ; GET `/api/factures/{id}/pdf/` |
| GET | `/api/dashboard/` |

Codes : `400` données invalides · `401` non authentifié · `403` interdit · `404` introuvable · `409` conflit (chambre déjà réservée) · `429` trop de tentatives.

## Tests
```bash
cd backend && python manage.py test        # 85 tests, base PostgreSQL de test créée automatiquement
cd frontend && npm run build               # vérifie que le frontend compile
```
Couvre : validations, prix serveur, minimum 20 000 Ar, dates, capacité, permissions, paiements, factures, contraintes SQL,
double réservation et **réservations simultanées réelles** (8 connexions PostgreSQL en parallèle sur la même chambre).

## Migrer des données depuis l'ancienne version MySQL
Sur l'**ancienne** installation (MySQL) :
```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission \
  -e admin.logentry -e sessions -e token_blacklist --indent 1 -o data.json
```
Sur la **nouvelle** (PostgreSQL) :
```bash
python manage.py migrate
python manage.py loaddata data.json
```
Si une migration échoue, c'est qu'une donnée viole une règle devenue stricte : deux réservations actives qui se chevauchent
sur une même chambre, ou deux e-mails identiques à la casse près. Corrigez-les dans le JSON (ou l'ancienne base) puis relancez.
Les fichiers `backend/media/` (images) se copient tels quels.

## Sauvegarde
Voir `backups/README.md` (`pg_dump` / `pg_restore`).

## Mise en production (rappels)
`DEBUG=False`, `SECRET_KEY` unique, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` et `CSRF_TRUSTED_ORIGINS` du vrai domaine, HTTPS
(les cookies sécurisés/HSTS s'activent automatiquement), `PAIEMENT_SIMULE=False`, serveur WSGI (`gunicorn config.wsgi`),
`python manage.py collectstatic`, sauvegardes planifiées. Changez ou supprimez les comptes de démonstration.

## Structure
```
hotel-reservation/
├── backend/   (config/, apps/{authentication,clients,chambres,reservations,paiements,factures,dashboard,common})
├── frontend/  (src/{components,pages,layouts,services,lib,context,routes})
├── database/schema.sql      schéma PostgreSQL de référence (généré par pg_dump)
├── docker-compose.yml       PostgreSQL local
└── backups/README.md
```


## Version 2
Voir `CHANGELOG_V2.md` : sécurité du retour arrière, nouveau design, CIN à 14 chiffres, bouton « À propos » (PDF du MPD, `frontend/public/docs/mpd.pdf`).
