import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { PageLoader } from './components/PageLoader'

const PatientLayout = lazy(() =>
  import('./components/PatientLayout').then((module) => ({
    default: module.PatientLayout,
  })),
)
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({
    default: module.DashboardPage,
  })),
)
const AdminDoctorsPage = lazy(() =>
  import('./pages/AdminDoctorsPage').then((module) => ({
    default: module.AdminDoctorsPage,
  })),
)
const DoctorDashboardPage = lazy(() =>
  import('./pages/DoctorDashboardPage').then((module) => ({
    default: module.DoctorDashboardPage,
  })),
)
const DoctorDetailPage = lazy(() =>
  import('./pages/DoctorDetailPage').then((module) => ({
    default: module.DoctorDetailPage,
  })),
)
const DoctorDirectoryPage = lazy(() =>
  import('./pages/DoctorDirectoryPage').then((module) => ({
    default: module.DoctorDirectoryPage,
  })),
)
const DoctorRegisterPage = lazy(() =>
  import('./pages/DoctorRegisterPage').then((module) => ({
    default: module.DoctorRegisterPage,
  })),
)
const LandingPage = lazy(() =>
  import('./pages/LandingPage').then((module) => ({
    default: module.LandingPage,
  })),
)
const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })),
)
const MedicalRecordsPage = lazy(() =>
  import('./pages/MedicalRecordsPage').then((module) => ({
    default: module.MedicalRecordsPage,
  })),
)
const NotFoundPage = lazy(() =>
  import('./pages/NotFoundPage').then((module) => ({
    default: module.NotFoundPage,
  })),
)
const ProfilePage = lazy(() =>
  import('./pages/ProfilePage').then((module) => ({
    default: module.ProfilePage,
  })),
)
const StaffLayout = lazy(() =>
  import('./components/StaffLayout').then((module) => ({
    default: module.StaffLayout,
  })),
)
const RegisterPage = lazy(() =>
  import('./pages/RegisterPage').then((module) => ({
    default: module.RegisterPage,
  })),
)

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/register/doctor" element={<DoctorRegisterPage />} />
            <Route path="/doctors" element={<DoctorDirectoryPage />} />
            <Route path="/doctors/:doctorId" element={<DoctorDetailPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <PatientLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route
                path="/medical-records"
                element={<MedicalRecordsPage />}
              />
            </Route>
            <Route
              element={
                <ProtectedRoute allowedRoles={['DOCTOR']}>
                  <StaffLayout role="DOCTOR" />
                </ProtectedRoute>
              }
            >
              <Route path="/doctor/dashboard" element={<DoctorDashboardPage />} />
            </Route>
            <Route
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <StaffLayout role="ADMIN" />
                </ProtectedRoute>
              }
            >
              <Route path="/admin/doctors" element={<AdminDoctorsPage />} />
            </Route>
            <Route path="/app" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
