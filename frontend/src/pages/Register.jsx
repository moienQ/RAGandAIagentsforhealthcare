import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signUp } from '../lib/supabase';

export default function Register() {
    const [form, setForm] = useState({ name: '', email: '', password: '', specialty: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await signUp(form.email, form.password, { full_name: form.name, specialty: form.specialty });
            navigate('/dashboard');
        } catch (err) {
            setError(err.message || 'Registration failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">
                    <div className="auth-logo-icon">🔬</div>
                    <h1 className="auth-title">Create Account</h1>
                    <p className="auth-sub">Join thousands of doctors using AI diagnostics</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Full name</label>
                        <input type="text" className="form-input" placeholder="Dr. Priya Sharma" value={form.name} onChange={set('name')} required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input type="email" className="form-input" placeholder="doctor@hospital.com" value={form.email} onChange={set('email')} required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Specialty</label>
                        <select className="form-select" value={form.specialty} onChange={set('specialty')}>
                            <option value="">Select specialty</option>
                            <option>Radiology</option>
                            <option>Cardiology</option>
                            <option>Neurology</option>
                            <option>General Medicine</option>
                            <option>Pulmonology</option>
                            <option>Oncology</option>
                            <option>Other</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input type="password" className="form-input" placeholder="Min. 8 characters" value={form.password} onChange={set('password')} required minLength={8} />
                    </div>

                    {error && (
                        <div style={{ background: 'rgba(239,68,68,.12)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '10px 14px', color: '#f87171', fontSize: '.875rem' }}>
                            {error}
                        </div>
                    )}

                    <button type="submit" className="btn btn-primary btn-lg" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
                        {loading ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>

                <p style={{ textAlign: 'center', marginTop: 24, fontSize: '.875rem', color: 'var(--text-muted)' }}>
                    Already have an account? <Link to="/login" className="auth-link">Sign in</Link>
                </p>
            </div>
        </div>
    );
}
