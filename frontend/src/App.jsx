import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import useReveal from './lib/useReveal';
import ProtectedRoute from './routes/ProtectedRoute';
import PublicLayout from './layouts/PublicLayout';
import DashboardLayout from './layouts/DashboardLayout';
import { Home, Login, Register, RoomDetail, Rooms } from './pages/Public';
import { NewReservation, Profile, ReservationDetail } from './pages/Espace';
import DashboardPage from './pages/Dashboard';
import { CategoriesPage, ChambresPage, ClientsPage, EquipementsPage, FacturesPage, PaiementsPage, ReservationsPage, ServicesPage, UsersPage } from './pages/Manage';

const STAFF = ['ADMIN', 'RECEPTIONNISTE'];

export default function App() {
  useReveal(); // apparition progressive des cartes au défilement
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<Home />} />
        <Route path="chambres" element={<Rooms />} />
        <Route path="chambres/:id" element={<RoomDetail />} />
        <Route path="disponibilite" element={<Rooms />} />
        <Route path="connexion" element={<Login />} />
        <Route path="inscription" element={<Register />} />
      </Route>

      <Route path="espace" element={<ProtectedRoute roles={['CLIENT']}><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="profil" element={<Profile />} />
        <Route path="reservations" element={<ReservationsPage />} />
        <Route path="reservations/nouvelle" element={<NewReservation />} />
        <Route path="reservations/:id" element={<ReservationDetail />} />
        <Route path="paiements" element={<PaiementsPage />} />
        <Route path="factures" element={<FacturesPage />} />
      </Route>

      <Route path="admin" element={<ProtectedRoute roles={STAFF}><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="chambres" element={<ChambresPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="reservations" element={<ReservationsPage />} />
        <Route path="paiements" element={<PaiementsPage />} />
        <Route path="factures" element={<FacturesPage />} />
        <Route path="profil" element={<Profile />} />
        <Route element={<ProtectedRoute roles={['ADMIN']}><Outlet /></ProtectedRoute>}>
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="equipements" element={<EquipementsPage />} />
          <Route path="services" element={<ServicesPage />} />
          <Route path="utilisateurs" element={<UsersPage />} />
          <Route path="statistiques" element={<DashboardPage view="stats" />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
