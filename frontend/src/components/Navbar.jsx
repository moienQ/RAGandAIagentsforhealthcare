import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { signOut } from '../lib/supabase';
import { Activity, LogOut, LayoutDashboard, FileScan, History } from 'lucide-react';

export default function Navbar() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await signOut();
        navigate('/login');
    };

    return (
        <nav className="navbar" style={{ background: 'rgba(4, 8, 20, 0.7)' }}>
            <NavLink to="/dashboard" className="navbar-logo" style={{ gap: '12px' }}>
                <div className="navbar-logo-icon" style={{ width: '40px', height: '40px', boxShadow: 'var(--shadow-glow)' }}>
                    <Activity size={24} color="white" />
                </div>
                <span>MediVision <span className="text-gradient">AI</span></span>
            </NavLink>

            <div className="navbar-nav">
                <NavLink to="/dashboard" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <LayoutDashboard size={16} /> Dashboard
                </NavLink>
                <NavLink to="/upload" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileScan size={16} /> Analyze
                </NavLink>
                <NavLink to="/history" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <History size={16} /> History
                </NavLink>

                {user ? (
                    <button className="btn btn-ghost btn-sm" onClick={handleLogout} style={{ marginLeft: 16, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <LogOut size={16} /> Logout
                    </button>
                ) : (
                    <NavLink to="/login" className="btn btn-primary btn-sm" style={{ marginLeft: 16 }}>Login</NavLink>
                )}
            </div>
        </nav>
    );
}
