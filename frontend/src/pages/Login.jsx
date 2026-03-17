import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signIn } from '../lib/supabase';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await signIn(email, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err.message || 'Login failed. Check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    const handleDemo = () => navigate('/dashboard');

    return (
        <div className="auth-page">
            <div className="auth-left">
                <div className="auth-logo">
                    <div className="auth-logo-icon">🔬</div>
                    <h1 className="auth-title">MediVision <span className="text-gradient">AI</span></h1>
                    <p className="auth-sub">Sign in to access your advanced medical imaging dashboard.</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Email address</label>
                        <input
                            type="email" className="form-input" placeholder="doctor@hospital.com"
                            value={email} onChange={e => setEmail(e.target.value)} required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input
                            type="password" className="form-input" placeholder="••••••••"
                            value={password} onChange={e => setPassword(e.target.value)} required
                        />
                    </div>

                    {error && (
                        <div style={{ background: 'rgba(239,68,68,.12)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '12px 16px', color: '#f87171', fontSize: '.875rem', animation: 'fadeIn 0.3s ease' }}>
                            {error}
                        </div>
                    )}

                    <button type="submit" className="btn btn-primary btn-lg" disabled={loading} style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}>
                        {loading ? <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Authenticating...</> : 'Sign In'}
                    </button>
                </form>

                <div className="auth-divider">or</div>

                <button className="btn btn-ghost btn-lg" style={{ width: '100%', justifyContent: 'center' }} onClick={handleDemo}>
                    🚀 Try Demo Mode (No Login)
                </button>

                <p style={{ textAlign: 'center', marginTop: 32, fontSize: '.9rem', color: 'var(--text-muted)' }}>
                    Don't have an account? <Link to="/register" className="auth-link">Create one for free</Link>
                </p>
            </div>

            <div className="auth-right">
                <div className="glass-panel auth-glass-card">
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 16 }}>Next-Generation Diagnostic Intelligence</h2>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <li style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                            <div style={{ background: 'rgba(45,212,191,0.2)', color: 'var(--teal-400)', padding: 6, borderRadius: 8, marginTop: 2 }}>✓</div>
                            <div>
                                <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Instant AI Analysis</h4>
                                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: 4 }}>Get detailed findings and differentials in seconds using Google Gemini.</p>
                            </div>
                        </li>
                        <li style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                            <div style={{ background: 'rgba(59,130,246,0.2)', color: 'var(--blue-400)', padding: 6, borderRadius: 8, marginTop: 2 }}>✓</div>
                            <div>
                                <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Multimodal Support</h4>
                                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: 4 }}>Analyze X-Rays, MRIs, CT Scans, and PDF Lab Reports effortlessly.</p>
                            </div>
                        </li>
                        <li style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                            <div style={{ background: 'rgba(167,139,250,0.2)', color: '#a78bfa', padding: 6, borderRadius: 8, marginTop: 2 }}>✓</div>
                            <div>
                                <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Secure History</h4>
                                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: 4 }}>All your patient scans and AI reports are securely stored and searchable.</p>
                            </div>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    );
}
