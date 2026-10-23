# Version 2 — récapitulatif des modifications

Quatre évolutions : sécurité du retour arrière, design et animations, CIN à 14 chiffres, bouton « À propos » (PDF du MPD).
Tests : 92 tests backend OK (85 d'origine + 7 nouveaux) ; parcours vérifié dans un navigateur piloté (connexion, déconnexion,
bouton « Retour », session expirée, CIN, « À propos », mobile) ; `npm run build` OK.

## 1. Retour arrière / sécurité de session
| Fichier | Modification |
|---|---|
| `backend/apps/common/middleware.py` (nouveau) | `NoCacheMiddleware` : `Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private`, `Pragma: no-cache`, `Expires` sur `/api/` et `/admin/` |
| `backend/config/settings.py` | Déclare le middleware (une ligne) |
| `frontend/vite.config.js`, `frontend/index.html`, `frontend/public/_headers` | Mêmes en-têtes pour les pages du site (serveur Vite, balises meta, hébergement statique) ; rechargement si la page est restaurée par le cache « avant/arrière » |
| `frontend/src/context/AuthContext.jsx` | `signOut()` (déconnexion + retour à la connexion sans historique), `endSession()`, réaction à `pageshow` et à la déconnexion dans un autre onglet |
| `frontend/src/routes/ProtectedRoute.jsx` | Session revérifiée auprès du serveur à chaque retour/avance du navigateur ; redirection si jeton absent |
| `frontend/src/lib/useBlockBack.js` (nouveau) | `history.pushState` + `popstate` : le bouton « Retour » ne quitte plus la page de connexion juste après une déconnexion |
| `frontend/src/services/api.js` | Session expirée : `location.replace('/connexion?session=expiree')` ; `clearSession()` ne supprime que les jetons |
| `frontend/src/pages/Public.jsx` | Connexion/Inscription : redirection si déjà connecté ; messages « déconnecté » et « session expirée » |
| `frontend/src/layouts/*.jsx` | Boutons « Déconnexion » → `signOut()` |

## 2. Design et animations
| Fichier | Modification |
|---|---|
| `frontend/src/index.css` | Réécriture complète : typographie fluide, espacements, ombres à deux niveaux, boutons (survol, appui, reflet), formulaires, tableaux, modales, menu, animations d'entrée ; respect de `prefers-reduced-motion` |
| `frontend/src/lib/useReveal.js` (nouveau), `App.jsx` | Apparition progressive des cartes au défilement |
| `frontend/src/components/CountUp.jsx` (nouveau), `pages/Dashboard.jsx` | Compteurs animés ; axe des revenus élargi (montants coupés) |
| `frontend/src/layouts/PublicLayout.jsx`, `DashboardLayout.jsx` | Barre de navigation à ombre au défilement, transition entre pages, menu latéral réductible par une flèche (choix mémorisé), barre supérieure fixe |
| Correctifs | Les cartes de chambres retrouvent leur effet de survol (l'animation d'entrée gardait son état final) ; fenêtres modales visibles et défilantes (variables Bootstrap manquantes) |

## 3. CIN : exactement 14 chiffres
| Fichier | Modification |
|---|---|
| `backend/apps/common/validators.py` | `valider_cin()` (remplace `valider_piece_identite`, alias conservé) : `[0-9]{14}` strict ; vide → NULL |
| `backend/apps/clients/serializers.py` | Utilise `valider_cin` |
| `frontend/src/lib/validators.js` | `validateCIN`, `digitsOnly`, `CIN_LENGTH` |
| `frontend/src/pages/Manage.jsx`, `components/CrudPage.jsx` | Champ « N° CIN » : clavier numérique, `pattern`, `maxlength=14`, saisie filtrée sur les chiffres, message d'erreur. Champ « Sexe » désormais marqué obligatoire (il l'était côté serveur) |
| `backend/apps/chambres/management/commands/seed_demo.py`, `apps/clients/tests.py`, `apps/common/tests.py` | Données de démo à 14 chiffres ; tests de la règle |

Le CIN reste **facultatif** (comme avant). Pour le rendre obligatoire : `required: true` sur ce champ dans `Manage.jsx`
et `allow_blank=False, allow_null=False` dans `ClientSerializer`. Les clients existants gardent leur ancien numéro, mais le
modifier exigera 14 chiffres.

## 4. Bouton « À propos » + PDF du MPD
| Fichier | Modification |
|---|---|
| `frontend/src/components/AboutModal.jsx` (nouveau) | Fenêtre modale avec lecteur PDF intégré (`<iframe>`), télécharger, nouvel onglet, agrandir/réduire, fermeture par Échap, focus géré |
| `frontend/src/layouts/PublicLayout.jsx`, `DashboardLayout.jsx` | Bouton « À propos » (navigation publique et tableau de bord) |
| `frontend/public/docs/mpd.pdf` (nouveau) | **Aucun PDF de MPD n'était fourni** : celui-ci est généré depuis `database/schema.sql` (diagramme A3 + dictionnaire des données). Pour utiliser le vôtre, remplacez simplement ce fichier |
| `database/generate_mpd_pdf.py` (nouveau) | Régénère le PDF : `python database/generate_mpd_pdf.py` |

## Divers
- `.gitignore` : exclut aussi `backups/*.dump` et `backups/*.sql` (les sauvegardes contiennent les données).
- Aucune nouvelle dépendance Python ou npm : `pip install` / `npm install` ne sont pas nécessaires si l'environnement existe déjà.
- Le fichier `backend/.env` n'est pas fourni : conservez le vôtre.
