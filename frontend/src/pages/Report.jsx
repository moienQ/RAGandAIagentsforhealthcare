import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { jsPDF } from 'jspdf';
import Navbar from '../components/Navbar';
import { ShieldAlert, Activity, AlertTriangle, CheckCircle, Download, ArrowLeft, HeartPulse, Stethoscope, FileText, Brain } from 'lucide-react';

const URGENCY_CONFIG = {
    CRITICAL: { cls: 'urgency-critical', icon: <ShieldAlert size={20} />, text: 'CRITICAL — Immediate physician review required' },
    URGENT: { cls: 'urgency-urgent', icon: <AlertTriangle size={20} />, text: 'URGENT — Prompt clinical correlation advised' },
    ROUTINE: { cls: 'urgency-routine', icon: <CheckCircle size={20} />, text: 'ROUTINE — No acute abnormalities detected' },
};

const SEVERITY_CLASSES = {
    CRITICAL: 'finding-critical',
    URGENT: 'finding-urgent',
    MONITOR: 'finding-monitor',
    NORMAL: 'finding-normal',
};

const SEVERITY_COLORS = {
    CRITICAL: '#ef4444',
    URGENT: '#f59e0b',
    MONITOR: '#3b82f6',
    NORMAL: '#10b981',
};

function FindingItem({ finding }) {
    const cls = SEVERITY_CLASSES[finding.severity] || 'finding-monitor';
    const badge = { CRITICAL: 'badge-critical', URGENT: 'badge-urgent', MONITOR: 'badge-monitor', NORMAL: 'badge-normal' }[finding.severity] || '';
    const color = SEVERITY_COLORS[finding.severity] || '#3b82f6';

    return (
        <div className={`finding-item ${cls}`} style={{ display: 'flex', gap: 16, padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', marginBottom: 12, border: '1px solid var(--border)', transition: 'background 0.2s' }}>
            <div style={{ flexShrink: 0, marginTop: 2 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, boxShadow: `0 0 10px ${color}80` }} />
            </div>
            <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 6 }}>
                    <span style={{ fontSize: '1rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>{finding.description}</span>
                    <span className={`badge ${badge}`} style={{ flexShrink: 0, fontSize: '0.75rem', padding: '4px 10px' }}>{finding.severity}</span>
                </div>
                {finding.location && (
                    <div style={{ fontSize: '.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Activity size={14} /> {finding.location}
                    </div>
                )}
            </div>
        </div>
    );
}

function parseLikelihood(s) {
    const n = parseInt(s?.replace('%', ''));
    return isNaN(n) ? 50 : n;
}

export default function Report() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        const stored = sessionStorage.getItem('lastAnalysis');
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                setData(parsed.result);
            } catch { setError('Failed to load analysis data.'); }
        } else {
            setError('Analysis data not found. Please run a new analysis.');
        }
    }, [id]);

    const downloadPDF = () => {
        if (!data) return;
        const doc = new jsPDF({ unit: 'mm', format: 'a4' });
        const lm = 20, rm = 190, tw = rm - lm;

        // PDF Styling (Dark theme colors simulated)
        doc.setFillColor(15, 20, 35); doc.rect(0, 0, 210, 297, 'F');
        doc.setFontSize(22); doc.setTextColor(20, 184, 166);
        doc.text('MediVision AI — Diagnostic Report', lm, 26);

        doc.setFontSize(10); doc.setTextColor(148, 163, 184);
        doc.text(`Report Generated: ${new Date().toLocaleString()}`, lm, 36);
        doc.text(`Modality: ${data.scan_type?.replace('_', ' ').toUpperCase() || 'Unknown'}`, lm, 42);
        doc.text(`AI Confidence: ${data.confidence}%  |  System Urgency: ${data.urgency}`, lm, 48);

        if (data.patient_info?.name && data.patient_info.name !== 'Anonymous') {
            doc.text(`Patient Identifier: ${data.patient_info.name}${data.patient_info.age ? `, ${data.patient_info.age}y` : ''}${data.patient_info.gender ? ` (${data.patient_info.gender})` : ''}`, lm, 54);
        }

        doc.setDrawColor(20, 184, 166); doc.setLineWidth(.5); doc.line(lm, 60, rm, 60);

        let y = 70;
        const section = (title) => {
            if (y > 270) { doc.addPage(); doc.setFillColor(15, 20, 35); doc.rect(0, 0, 210, 297, 'F'); y = 20; }
            doc.setFontSize(12); doc.setTextColor(255, 255, 255); doc.setFont(undefined, 'bold');
            doc.text(title, lm, y); y += 8;
            doc.setFont(undefined, 'normal'); doc.setFontSize(10); doc.setTextColor(203, 213, 225);
        };
        const line = (text) => {
            const lines = doc.splitTextToSize(text, tw);
            if (y + (lines.length * 6) > 280) { doc.addPage(); doc.setFillColor(15, 20, 35); doc.rect(0, 0, 210, 297, 'F'); y = 20; }
            doc.text(lines, lm, y); y += lines.length * 5.5 + 3;
        };

        section('CLINICAL IMPRESSION');
        line(data.impression || 'Notes unavailable.');
        y += 6;

        section('KEY FINDINGS');
        (data.findings || []).forEach((f, i) => {
            line(`${i + 1}. [${f.severity}] ${f.description}${f.location ? ` (Location: ${f.location})` : ''}`);
        });
        y += 6;

        section('DIFFERENTIAL DIAGNOSES');
        (data.differentials || []).forEach((d, i) => {
            line(`• ${d.diagnosis} (Likelihood: ${d.likelihood})`);
        });
        y += 6;

        section('RECOMMENDED ACTIONS');
        (data.recommendations || []).forEach((r, i) => line(`${i + 1}. ${r}`));
        y += 10;

        doc.setFontSize(8); doc.setTextColor(100, 116, 139);
        doc.text('MEDICAL DISCLAIMER: For informational purposes only. Clinical correlation required.', lm, y);

        doc.save(`MediVision_Report_${data.patient_info?.name || 'Anonymous'}_${new Date().toISOString().slice(0, 10)}.pdf`);
    };

    if (error) return (
        <div className="page"><Navbar />
            <div className="container" style={{ paddingTop: 80, textAlign: 'center', animation: 'fadeInUp 0.4s ease' }}>
                <div style={{ display: 'inline-block', padding: 24, borderRadius: '50%', background: 'rgba(239,68,68,0.1)', color: '#ef4444', marginBottom: 24 }}>
                    <AlertTriangle size={48} />
                </div>
                <h2 style={{ fontSize: '1.5rem', marginBottom: 12 }}>{error}</h2>
                <Link to="/upload" className="btn btn-primary btn-lg" style={{ marginTop: 24, display: 'inline-flex' }}>Upload New Scan</Link>
            </div>
        </div>
    );

    if (!data) return (
        <div className="page"><Navbar />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: 16 }}>
                <div className="spinner" style={{ width: 48, height: 48, borderColor: 'var(--teal-400)', borderRightColor: 'transparent' }} />
                <div style={{ color: 'var(--text-secondary)' }}>Loading diagnostic data...</div>
            </div>
        </div>
    );

    const urgency = URGENCY_CONFIG[data.urgency] || URGENCY_CONFIG.ROUTINE;

    return (
        <div className="page" style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', top: -50, right: '10%', width: 600, height: 600, background: 'radial-gradient(circle, rgba(20,184,166,0.1) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />
            <Navbar />
            <div className="container" style={{ paddingTop: 40, paddingBottom: 80, position: 'relative', zIndex: 1 }}>

                {/* Header Actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32, animation: 'fadeInUp 0.3s ease forwards' }}>
                    <Link to="/dashboard" className="btn btn-ghost" style={{ display: 'flex', gap: 8, color: 'var(--text-secondary)' }}>
                        <ArrowLeft size={16} /> Back to Dashboard
                    </Link>
                    <div style={{ display: 'flex', gap: 12 }}>
                        <Link to="/upload" className="btn btn-ghost">New Analysis</Link>
                        <button className="btn btn-primary" onClick={downloadPDF} style={{ display: 'flex', gap: 8 }}>
                            <Download size={16} /> Export PDF
                        </button>
                    </div>
                </div>

                {/* Patient & Scan Info Header */}
                <div className="card glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 24, marginBottom: 24, padding: '32px 40px', animation: 'fadeInUp 0.4s ease forwards' }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, color: 'var(--teal-400)' }}>
                            <FileText size={20} />
                            <span style={{ fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', fontSize: '0.85rem' }}>
                                {data.scan_type?.replace('_', ' ')} Report
                            </span>
                        </div>
                        <h1 style={{ fontSize: '2.4rem', fontWeight: 800, margin: '8px 0', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                            {data.patient_info?.name || 'Anonymous Patient'}
                        </h1>
                        <div style={{ display: 'flex', gap: 16, color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: 12 }}>
                            {data.patient_info?.age && <span>{data.patient_info.age} years old</span>}
                            {data.patient_info?.gender && <span>• {data.patient_info.gender}</span>}
                            <span>• ID: {id !== 'latest' && id ? id.slice(0, 8).toUpperCase() : `AI-${Math.floor(Math.random() * 10000)}`}</span>
                        </div>
                    </div>

                    <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div className={`urgency-banner ${urgency.cls}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: '8px', fontSize: '0.9rem', fontWeight: 600, border: '1px solid currentColor', background: 'rgba(0,0,0,0.2)' }}>
                            {urgency.icon}
                            {urgency.text}
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                            Report Date: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                        </div>
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 24, alignItems: 'start' }}>

                    {/* Left Column: Impression, Findings, Recommendations */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, animation: 'fadeInUp 0.5s ease forwards', animationDelay: '0.1s', opacity: 0 }}>
                        <div className="card glass-panel" style={{ padding: '32px' }}>
                            <h3 style={{ fontWeight: 700, marginBottom: 20, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
                                <Stethoscope size={22} color="var(--blue-400)" /> Clinical Impression
                            </h3>
                            <p style={{ color: 'var(--text-primary)', lineHeight: 1.8, fontSize: '1.05rem', fontWeight: 400 }}>
                                {data.impression}
                            </p>
                        </div>

                        <div className="card glass-panel" style={{ padding: '32px' }}>
                            <h3 style={{ fontWeight: 700, marginBottom: 20, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
                                <Activity size={22} color="var(--teal-400)" /> Detailed Findings
                            </h3>
                            {(data.findings || []).length === 0 ? (
                                <p style={{ color: 'var(--text-muted)', padding: '20px 0' }}>No significant findings reported.</p>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', marginTop: 8 }}>
                                    {(data.findings || []).map((f, i) => <FindingItem key={i} finding={f} />)}
                                </div>
                            )}
                        </div>

                        <div className="card glass-panel" style={{ padding: '32px' }}>
                            <h3 style={{ fontWeight: 700, marginBottom: 20, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
                                <CheckCircle size={22} color="var(--green-400)" /> Recommendations
                            </h3>
                            <ol style={{ paddingLeft: 24, display: 'flex', flexDirection: 'column', gap: 14, margin: 0 }}>
                                {(data.recommendations || []).map((r, i) => (
                                    <li key={i} style={{ color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: 1.6, paddingLeft: 8 }}>{r}</li>
                                ))}
                            </ol>
                        </div>
                    </div>

                    {/* Right Column: AI Confidence, Differentials Components */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, animation: 'fadeInUp 0.6s ease forwards', animationDelay: '0.2s', opacity: 0 }}>
                        <div className="card glass-panel" style={{ background: 'linear-gradient(180deg, rgba(20,184,166,0.05), transparent)' }}>
                            <h3 style={{ fontWeight: 700, marginBottom: 24, fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: 10 }}>
                                <Brain size={20} color="var(--teal-400)" /> AI Diagnostic Confidence
                            </h3>

                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px 0' }}>
                                <div style={{ position: 'relative', width: 140, height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <svg viewBox="0 0 100 100" style={{ position: 'absolute', inset: 0, transform: 'rotate(-90deg)', overflow: 'visible' }}>
                                        <circle cx="50" cy="50" r="45" fill="none" stroke="var(--border)" strokeWidth="6" />
                                        <circle cx="50" cy="50" r="45" fill="none" stroke="url(#gradient)" strokeWidth="6" strokeDasharray="283" strokeDashoffset={283 - (283 * data.confidence) / 100} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1.5s ease-in-out' }} />
                                        <defs>
                                            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                                <stop offset="0%" stopColor="var(--blue-400)" />
                                                <stop offset="100%" stopColor="var(--teal-400)" />
                                            </linearGradient>
                                        </defs>
                                    </svg>
                                    <div style={{ textAlign: 'center' }}>
                                        <div className="text-gradient" style={{ fontSize: '2.5rem', fontWeight: 800, lineHeight: 1 }}>{data.confidence}%</div>
                                    </div>
                                </div>
                            </div>

                            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: 12 }}>
                                Model confidence based on pattern clarity and training data correlation.
                            </div>
                        </div>

                        <div className="card glass-panel">
                            <h3 style={{ fontWeight: 700, marginBottom: 20, fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: 10 }}>
                                <HeartPulse size={20} color="var(--blue-400)" /> Differential Diagnoses
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                                {(data.differentials || []).map((d, i) => {
                                    const pct = parseLikelihood(d.likelihood);
                                    return (
                                        <div key={i}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                                <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>{d.diagnosis}</span>
                                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{d.likelihood}</span>
                                            </div>
                                            <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 99, overflow: 'hidden' }}>
                                                <div style={{ height: '100%', width: `${pct}%`, background: pct > 60 ? 'var(--blue-400)' : pct > 30 ? 'var(--cyan-500)' : 'var(--text-muted)', borderRadius: 99, transition: 'width 1s ease' }} />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="glass-panel" style={{ background: 'rgba(251,191,36,.05)', border: '1px solid rgba(251,191,36,.2)', borderRadius: '16px', padding: '20px', fontSize: '.85rem', color: 'var(--text-secondary)', display: 'flex', gap: 16 }}>
                            <AlertTriangle size={24} color="var(--amber-400)" style={{ flexShrink: 0 }} />
                            <div style={{ lineHeight: 1.6 }}>
                                <strong style={{ color: 'var(--amber-400)' }}>CLINICAL DISCLAIMER</strong><br />
                                This Artificial Intelligence analysis is supplementary and intended for investigational/assistance purposes only. It does not replace the professional judgement of a certified radiologist/clinician.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
