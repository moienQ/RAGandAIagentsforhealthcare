import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { getDashboardStats, getHistory } from '../api/client';
import { ShieldAlert, Activity, Calendar, Zap, FileJson, Stethoscope, Microscope, Brain, FileBox, ChevronRight } from 'lucide-react';

const SCAN_ICONS = { chest_xray: <Activity size={24} />, mri_brain: <Brain size={24} />, ct_scan: <Microscope size={24} />, lab_report: <FileJson size={24} />, ecg: <Stethoscope size={24} /> };
const SCAN_LABELS = { chest_xray: 'Chest X-Ray', mri_brain: 'Brain MRI', ct_scan: 'CT Scan', lab_report: 'Lab Report', ecg: 'ECG' };

function UrgencyBadge({ urgency }) {
    const cls = { CRITICAL: 'badge-critical', URGENT: 'badge-urgent', ROUTINE: 'badge-normal' }[urgency] || 'badge-routine';
    return <span className={`badge ${cls}`}>{urgency}</span>;
}

export default function Dashboard() {
    const { user } = useAuth();
    const [stats, setStats] = useState({ total: 0, this_month: 0, critical: 0 });
    const [recent, setRecent] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!user?.id) { setLoading(false); return; }
        Promise.all([
            getDashboardStats(user.id).catch(() => ({ total: 0, this_month: 0, critical: 0 })),
            getHistory({ userId: user.id, limit: 5 }).catch(() => ({ data: [] }))
        ]).then(([s, h]) => {
            setStats(s);
            setRecent(h.data || []);
            setLoading(false);
        });
    }, [user]);

    const greeting = user?.user_metadata?.full_name
        ? `Welcome back, Dr. ${user.user_metadata.full_name.split(' ').slice(-1)[0]}!`
        : 'Welcome to MediVision AI!';

    return (
        <div className="page" style={{ position: 'relative' }}>
            {/* Background Glows */}
            <div style={{ position: 'absolute', top: -150, left: '10%', width: 500, height: 500, background: 'radial-gradient(circle, rgba(20,184,166,0.1) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />
            <div style={{ position: 'absolute', top: 200, right: '5%', width: 600, height: 600, background: 'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />

            <div style={{ position: 'relative', zIndex: 1 }}>
                <Navbar />
                <div className="container" style={{ paddingTop: 40, paddingBottom: 60 }}>

                    {/* Header */}
                    <div style={{ marginBottom: 40, animation: 'fadeInUp 0.4s ease forwards' }}>
                        <h1 className="page-title">{greeting}</h1>
                        <p className="page-subtitle">Your intelligent medical imaging and diagnosis workspace.</p>
                    </div>

                    {/* Hero CTA */}
                    <div className="card glass-panel" style={{
                        background: 'linear-gradient(135deg, rgba(20,184,166,.1), rgba(59,130,246,.1))',
                        borderColor: 'var(--border-hover)',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20, marginBottom: 40,
                        animation: 'fadeInUp 0.5s ease forwards', animationDelay: '0.1s', opacity: 0
                    }}>
                        <div>
                            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
                                <Zap className="text-gradient" size={28} /> Start New Analysis
                            </h2>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '.95rem' }}>Upload X-rays, MRIs, CT scans, or laboratory PDF reports for instant AI-powered findings.</p>
                        </div>
                        <Link to="/upload" className="btn btn-primary btn-lg" style={{ borderRadius: 'var(--radius-md)' }}>
                            Analyze Scan
                        </Link>
                    </div>

                    {/* Stats */}
                    <div className="grid-3" style={{ marginBottom: 40, animation: 'fadeInUp 0.6s ease forwards', animationDelay: '0.2s', opacity: 0 }}>
                        <div className="stat-card glass-panel" style={{ background: 'var(--bg-card)', padding: '24px 28px' }}>
                            <div className="stat-icon" style={{ background: 'rgba(20,184,166,.15)', color: 'var(--teal-400)', boxShadow: '0 0 20px rgba(20,184,166,0.2)' }}>
                                <FileBox size={24} />
                            </div>
                            <div>
                                <div className="stat-number">{loading ? '–' : stats.total}</div>
                                <div className="stat-label">Total Analyses</div>
                            </div>
                        </div>
                        <div className="stat-card glass-panel" style={{ background: 'var(--bg-card)', padding: '24px 28px' }}>
                            <div className="stat-icon" style={{ background: 'rgba(96,165,250,.15)', color: 'var(--blue-400)', boxShadow: '0 0 20px rgba(96,165,250,0.2)' }}>
                                <Calendar size={24} />
                            </div>
                            <div>
                                <div className="stat-number">{loading ? '–' : stats.this_month}</div>
                                <div className="stat-label">This Month</div>
                            </div>
                        </div>
                        <div className="stat-card glass-panel" style={{ background: 'var(--bg-card)', padding: '24px 28px' }}>
                            <div className="stat-icon" style={{ background: 'rgba(239,68,68,.15)', color: '#f87171', boxShadow: '0 0 20px rgba(239,68,68,0.2)' }}>
                                <ShieldAlert size={24} />
                            </div>
                            <div>
                                <div className="stat-number" style={{ color: stats.critical > 0 ? '#f87171' : 'inherit' }}>{loading ? '–' : stats.critical}</div>
                                <div className="stat-label">Critical Findings</div>
                            </div>
                        </div>
                    </div>

                    {/* Quick scan types */}
                    <div className="card glass-panel" style={{ marginBottom: 40, animation: 'fadeInUp 0.7s ease forwards', animationDelay: '0.3s', opacity: 0 }}>
                        <h3 style={{ fontWeight: 700, marginBottom: 24, fontSize: '1.15rem' }}>Supported Scanning Modalities</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16 }}>
                            {Object.entries(SCAN_LABELS).map(([k, label]) => (
                                <Link to="/upload" key={k} style={{ textDecoration: 'none' }}>
                                    <div className="scan-type-btn" style={{ padding: '24px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                        <div className="icon" style={{ color: 'var(--text-primary)' }}>{SCAN_ICONS[k]}</div>
                                        <div className="label" style={{ fontSize: '.85rem', marginTop: 12 }}>{label}</div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>

                    {/* Recent analyses */}
                    <div className="card glass-panel" style={{ animation: 'fadeInUp 0.8s ease forwards', animationDelay: '0.4s', opacity: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                            <h3 style={{ fontWeight: 700, fontSize: '1.15rem' }}>Recent Diagnostic Reports</h3>
                            <Link to="/history" className="btn btn-ghost btn-sm" style={{ display: 'flex', alignItems: 'center' }}>
                                View all <ChevronRight size={16} />
                            </Link>
                        </div>

                        {loading ? (
                            <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="spinner" /></div>
                        ) : recent.length === 0 ? (
                            <div className="empty-state" style={{ padding: '80px 20px' }}>
                                <div className="empty-icon text-gradient" style={{ display: 'inline-block' }}><Activity size={64} /></div>
                                <div className="empty-title" style={{ marginTop: 24, fontSize: '1.4rem' }}>No analyses completed yet</div>
                                <div className="empty-sub" style={{ fontSize: '1rem', marginTop: 8 }}>Upload your first medical scan to generate an AI report.</div>
                                <Link to="/upload" className="btn btn-primary btn-lg" style={{ marginTop: 32 }}>Analyze a Scan</Link>
                            </div>
                        ) : (
                            <div style={{ overflowX: 'auto' }}>
                                <table className="history-table">
                                    <thead>
                                        <tr>
                                            <th>Patient Identifier</th><th>Modality</th><th>AI Triage</th><th>Confidence</th><th>Date</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recent.map(a => (
                                            <tr key={a.id}>
                                                <td style={{ fontWeight: 600 }}>{a.patient_name}</td>
                                                <td style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '16px' }}>
                                                    <span style={{ color: 'var(--text-secondary)' }}>{SCAN_ICONS[a.scan_type]}</span> {SCAN_LABELS[a.scan_type]}
                                                </td>
                                                <td><UrgencyBadge urgency={a.urgency} /></td>
                                                <td><span style={{ color: 'var(--teal-400)', fontWeight: 700 }}>{a.confidence}%</span></td>
                                                <td style={{ color: 'var(--text-secondary)' }}>{new Date(a.created_at).toLocaleDateString()}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
