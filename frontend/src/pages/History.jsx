import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { getHistory } from '../api/client';
import { Activity, Brain, Microscope, FileJson, Stethoscope, Search, Filter, FolderOpen, ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react';

const SCAN_ICONS = { chest_xray: <Activity size={18} />, mri_brain: <Brain size={18} />, ct_scan: <Microscope size={18} />, lab_report: <FileJson size={18} />, ecg: <Stethoscope size={18} /> };
const SCAN_LABELS = { chest_xray: 'Chest X-Ray', mri_brain: 'Brain MRI', ct_scan: 'CT Scan', lab_report: 'Lab Report', ecg: 'ECG' };

function UrgencyBadge({ u }) {
    const m = { CRITICAL: 'badge-critical', URGENT: 'badge-urgent', ROUTINE: 'badge-normal' };
    return <span className={`badge ${m[u] || 'badge-routine'}`}>{u}</span>;
}

export default function History() {
    const { user } = useAuth();
    const [records, setRecords] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [scanFilter, setScanFilter] = useState('');
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        if (!user?.id) { setLoading(false); return; }
        setLoading(true);
        try {
            const res = await getHistory({ userId: user.id, page, limit: 15, scanType: scanFilter || undefined });
            setRecords(res.data || []);
            setTotal(res.total || 0);
        } catch {
            setRecords([]);
        } finally {
            setLoading(false);
        }
    }, [user, page, scanFilter]);

    useEffect(() => { load(); }, [load]);

    const filtered = search
        ? records.filter(r => r.patient_name?.toLowerCase().includes(search.toLowerCase()))
        : records;

    const totalPages = Math.ceil(total / 15);

    return (
        <div className="page" style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', top: -100, right: '-5%', width: 500, height: 500, background: 'radial-gradient(circle, rgba(167,139,250,0.06) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />
            <Navbar />
            <div className="container" style={{ paddingTop: 40, paddingBottom: 60, position: 'relative', zIndex: 1 }}>

                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16, marginBottom: 32, animation: 'fadeInUp 0.4s ease forwards' }}>
                    <div>
                        <h1 className="page-title">Diagnostic Archive</h1>
                        <p className="page-subtitle">View and search through {total} past AI medical analyses</p>
                    </div>
                    <Link to="/upload" className="btn btn-primary btn-lg" style={{ borderRadius: 'var(--radius-sm)' }}>+ New Analysis</Link>
                </div>

                {/* Filters */}
                <div className="card glass-panel card-sm" style={{ marginBottom: 32, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center', animation: 'fadeInUp 0.5s ease forwards', animationDelay: '0.1s', opacity: 0 }}>
                    <div style={{ position: 'relative', flex: 1, minWidth: 260 }}>
                        <Search size={18} color="var(--text-muted)" style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)' }} />
                        <input
                            className="form-input" placeholder="Search by patient identifier..."
                            value={search} onChange={e => setSearch(e.target.value)}
                            style={{ paddingLeft: 42, background: 'rgba(255,255,255,0.03)' }}
                        />
                    </div>
                    <div style={{ position: 'relative', width: 220 }}>
                        <Filter size={18} color="var(--text-muted)" style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', zIndex: 1 }} />
                        <select
                            className="form-select" value={scanFilter} onChange={e => { setScanFilter(e.target.value); setPage(1); }}
                            style={{ paddingLeft: 42, background: 'rgba(255,255,255,0.03)', appearance: 'none' }}
                        >
                            <option value="">All Modalities</option>
                            {Object.entries(SCAN_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                        </select>
                        <ChevronRight size={16} color="var(--text-muted)" style={{ position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%) rotate(90deg)' }} />
                    </div>
                    <button className="btn btn-ghost" onClick={() => { setSearch(''); setScanFilter(''); setPage(1); }}>
                        Clear Filters
                    </button>
                </div>

                {/* Table */}
                <div className="card glass-panel" style={{ padding: 0, overflow: 'hidden', animation: 'fadeInUp 0.6s ease forwards', animationDelay: '0.2s', opacity: 0 }}>
                    {loading ? (
                        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><div className="spinner" /></div>
                    ) : filtered.length === 0 ? (
                        <div className="empty-state" style={{ padding: '80px 32px' }}>
                            <div className="empty-icon text-gradient" style={{ display: 'inline-block' }}><FolderOpen size={64} /></div>
                            <div className="empty-title" style={{ marginTop: 24, fontSize: '1.4rem' }}>{user?.id ? 'No records found' : 'Login to view your history'}</div>
                            <div className="empty-sub" style={{ fontSize: '1rem', marginTop: 8 }}>{user?.id ? 'Try adjusting your search criteria.' : 'Your analyses will be securely stored here.'}</div>
                            <Link to={user?.id ? '/upload' : '/login'} className="btn btn-primary btn-lg" style={{ marginTop: 32 }}>
                                {user?.id ? 'Analyze a Scan' : 'Login Now'}
                            </Link>
                        </div>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table className="history-table">
                                <thead style={{ background: 'rgba(255,255,255,0.02)' }}>
                                    <tr>
                                        <th style={{ paddingLeft: 32 }}>Patient Identifier</th>
                                        <th>Modality</th>
                                        <th>AI Triage</th>
                                        <th>Confidence Result</th>
                                        <th>Analysis Date</th>
                                        <th style={{ textAlign: 'right', paddingRight: 32 }}>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map(r => (
                                        <tr key={r.id} style={{ transition: 'background 0.2s' }}>
                                            <td style={{ paddingLeft: 32, fontWeight: 600, color: 'var(--text-primary)' }}>
                                                {r.patient_name || 'Anonymous'}
                                                {r.patient_age && <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 8 }}>{r.patient_age}y</span>}
                                                {r.patient_gender && <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 4 }}>• {r.patient_gender}</span>}
                                            </td>
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-secondary)' }}>
                                                    <span style={{ color: 'var(--text-primary)' }}>{SCAN_ICONS[r.scan_type]}</span> {SCAN_LABELS[r.scan_type] || r.scan_type}
                                                </div>
                                            </td>
                                            <td><UrgencyBadge u={r.urgency} /></td>
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 99, overflow: 'hidden', minWidth: 60 }}>
                                                        <div style={{ height: '100%', background: 'var(--gradient-primary)', width: `${r.confidence}%` }} />
                                                    </div>
                                                    <span style={{ color: 'var(--teal-400)', fontWeight: 700, fontSize: '.9rem' }}>{r.confidence}%</span>
                                                </div>
                                            </td>
                                            <td style={{ color: 'var(--text-secondary)', fontSize: '.9rem' }}>
                                                {new Date(r.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })}
                                            </td>
                                            <td style={{ textAlign: 'right', paddingRight: 32 }}>
                                                <Link to={`/report/${r.id}`} className="btn btn-ghost btn-sm" style={{ padding: '6px 12px' }}>
                                                    View Report <ArrowRight size={14} />
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && !loading && (
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16, padding: '24px', borderTop: '1px solid var(--border)', background: 'rgba(255,255,255,0.01)' }}>
                            <button className="btn btn-ghost" disabled={page === 1} onClick={() => setPage(p => p - 1)} style={{ padding: '8px 16px' }}>
                                <ChevronLeft size={16} /> Previous
                            </button>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                {[...Array(totalPages)].map((_, i) => (
                                    <div key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: i + 1 === page ? 'var(--teal-400)' : 'rgba(255,255,255,0.2)', transition: 'background 0.2s' }} />
                                ))}
                            </div>
                            <button className="btn btn-ghost" disabled={page === totalPages} onClick={() => setPage(p => p + 1)} style={{ padding: '8px 16px' }}>
                                Next <ChevronRight size={16} />
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
