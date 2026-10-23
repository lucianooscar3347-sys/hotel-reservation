# Version PostgreSQL — ce qui a changé et pourquoi

## 1. Migration MySQL → PostgreSQL
- `settings.py` : moteur `django.db.backends.postgresql` (psycopg 3), port 5432, `CONN_MAX_AGE`, identifiants lus dans `.env`.
- `requirements.txt` : `mysqlclient` remplacé par `psycopg[binary]`. Django `>=5.1,<5.3` (l'ancienne borne `<5.0`
  contredisait les migrations générées avec Django 5.2). `gunicorn` ajouté.
- `config/__init__.py` : suppression du contournement XAMPP/MariaDB (`DatabaseWrapper.check_database_version_supported`).
- `database/schema.sql` : régénéré avec `pg_dump` (testé : se recharge sans erreur dans une base vide).
- `docker-compose.yml` (PostgreSQL 16) et `backups/README.md` (sauvegarde/restauration) ajoutés.
- Les montants restent en `NUMERIC` (`DecimalField`) : aucun calcul en virgule flottante.

## 2. Corrections et renforcements
| Problème | Correction |
|---|---|
| Double réservation protégée seulement par un verrou applicatif | **Contrainte d'exclusion PostgreSQL** `excl_resa_chevauchement` (extension `btree_gist`, migration `reservations/0003`) |
| Conflit de réservation renvoyé en 400 | **409 Conflict** ; une violation de contrainte à la dernière milliseconde est traduite en 409 propre (pas de 500) |
| « Aujourd'hui » calculé en UTC alors que l'hôtel est en UTC+3 | `TIME_ZONE = Indian/Antananarivo` (supporté nativement par PostgreSQL) |
| **Un client pouvait se déclarer « payé »** (fournisseur simulé qui accepte tout) | Paiement en ligne refusé tant qu'aucun vrai fournisseur n'existe (`PAIEMENT_SIMULE`) ; espèces/virement réservés à la réception |
| E-mails uniques mais sensibles à la casse en base | Index uniques sur `LOWER(email)` (utilisateurs et clients) |
| Devis `138000` vs réservation `138000.00` | Format de montants unifié (2 décimales) |
| Intégrité des réservations | CHECK : total > 0, au moins 1 adulte |
| Swagger (`/api/docs/`) plantait à la génération (utilisateur anonyme) | `swagger_fake_view` + annotations de schéma : 0 avertissement |
| Aucun réglage de sécurité HTTP pour la production | HTTPS, cookies sécurisés, HSTS, en-tête proxy (actifs quand `DEBUG=False`) |
| `CheckConstraint(check=…)` déprécié | `condition=` (Django 5.1+) |
| Bundle JS unique de 713 kB | Découpage en 4 fichiers (graphiques Recharts isolés dans leur propre fichier) |
| Test d'inscription périmé (prénom d'1 lettre, refusé par la validation) | Test corrigé |

## 3. Tests réellement exécutés (PostgreSQL 16, Python 3.12, Django 5.2)
- `python manage.py test` : **85 tests, tous OK** (avec les avertissements de dépréciation traités comme des erreurs).
  Dont 13 nouveaux : contrainte d'exclusion, CHECK SQL, colonnes NUMERIC, e-mail insensible à la casse, fuseau horaire,
  **8 requêtes simultanées sur la même chambre → 1 succès + 7 × 409**, 8 chambres différentes → 8 succès, sécurité des paiements.
- `npm run build` : OK.
- Schéma Swagger généré sans avertissement ; tableau de bord (agrégation mensuelle) vérifié sur PostgreSQL ;
  `dumpdata` → `loaddata` vérifié sur PostgreSQL.

## 4. Non exécuté / à faire chez vous
- Tests automatisés du frontend (aucun framework de test JS n'existe dans le projet) et tests de bout en bout dans un navigateur.
- Migration de **vos** données MySQL : la procédure est dans le README mais n'a pas pu être testée sur votre base.
- Branchement d'un vrai fournisseur de paiement (MVola, Orange Money, Airtel Money, carte) dans `apps/paiements/providers.py`.
- Déploiement (HTTPS, gunicorn, nginx) et sauvegardes planifiées.

## 5. Points inchangés (voir l'ancienne version)
Une réservation = une chambre ; pas de tarifs saisonniers ; facture PDF sans le détail des services ; taxes et réduction
long séjour désactivées par défaut (`.env`).
