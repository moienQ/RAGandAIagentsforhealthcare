import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { analyzeFile } from '../api/client';
import { UploadCloud, FileImage, FileText, CheckCircle, Activity, Brain, Microscope, FileJson, Stethoscope, AlertTriangle } from 'lucide-react';

const SCAN_TYPES = [
    { id: 'chest_xray', icon: <Activity size={24} />, label: 'Chest X-Ray' },
    { id: 'mri_brain', icon: <Brain size={24} />, label: 'Brain MRI' },
    { id: 'ct_scan', icon: <Microscope size={24} />, label: 'CT Scan' },
    { id: 'lab_report', icon: <FileJson size={24} />, label: 'Lab Report' },
    { id: 'ecg', icon: <Stethoscope size={24} />, label: 'ECG' },
];

const ANALYZING_STEPS = [
    'Preprocessing image data...',
    'Running deep learning pattern recognition...',
    'Analyzing anatomical structures...',
    'Cross-referencing critical pathologies...',
    'Generating final diagnostic report...',
];

export default function Upload() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [file, setFile] = useState(null);
    const [scanType, setScanType] = useState('chest_xray');
    const [patient, setPatient] = useState({ name: '', age: '', gender: '', history: '' });
    const [analyzing, setAnalyzing] = useState(false);
    const [step, setStep] = useState(0);
    const [error, setError] = useState('');

    const setP = (k) => (e) => setPatient(p => ({ ...p, [k]: e.target.value }));

    const onDrop = useCallback((accepted) => {
        if (accepted[0]) { setFile(accepted[0]); setError(''); }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/jpeg': [], 'image/png': [], 'image/webp': [], 'application/pdf': [] },
        maxFiles: 1,
        maxSize: 20 * 1024 * 1024
    });

    const handleAnalyze = async () => {
        if (!file) { setError('Please upload a file first.'); return; }
        setAnalyzing(true);
        setError('');
        setStep(0);

        const interval = setInterval(() => setStep(s => (s + 1) % ANALYZING_STEPS.length), 2000);

        try {
            const result = await analyzeFile({
                file,
                scanType,
                patientName: patient.name || undefined,
                patientAge: patient.age ? parseInt(patient.age) : undefined,
                patientGender: patient.gender || undefined,
                clinicalHistory: patient.history || undefined,
                userId: user?.id
            });

            clearInterval(interval);

            if (result.success) {
                sessionStorage.setItem('lastAnalysis', JSON.stringify(result));
                navigate(`/report/${result.analysis_id || 'latest'}`);
            } else {
                setError(result.error || 'Analysis failed. Please try again.');
                setAnalyzing(false);
            }
        } catch (err) {
            clearInterval(interval);
            setError(err.response?.data?.detail || err.message || 'Analysis failed. Check your API key and connection.');
            setAnalyzing(false);
        }
    };

    if (analyzing) return (
        <div className="page" style={{ position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: '20%', left: '50%', transform: 'translate(-50%, -50%)', width: 600, height: 600, background: 'radial-gradient(circle, rgba(20,184,166,0.15) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />
            <Navbar />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, padding: 40, position: 'relative', zIndex: 1 }}>
                <div className="card glass-panel analyzing-container" style={{ maxWidth: 500, width: '100%', animation: 'fadeInUp 0.5s ease forwards' }}>
                    <div className="scan-animation" style={{ borderColor: 'var(--border-glow)' }}>
                        <div className="scan-grid" />
                        <div className="scan-line" />
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--teal-400)' }}>
                            {SCAN_TYPES.find(s => s.id === scanType)?.icon}
                        </div>
                    </div>
                    <div style={{ textAlign: 'center', width: '100%' }}>
                        <div className="scan-text text-gradient">AI Analysis in Progress<span className="analyzing-dots" /></div>
                        <div className="scan-subtext" style={{ marginTop: 12, minHeight: 24, fontSize: '0.95rem', fontWeight: 500 }}>
                            {ANALYZING_STEPS[step]}
                        </div>
                    </div>
                    <div style={{ width: '100%', background: 'rgba(255,255,255,.06)', borderRadius: 99, height: 6, overflow: 'hidden', marginTop: 8 }}>
                        <div style={{ height: '100%', background: 'var(--gradient-primary)', borderRadius: 99, width: `${((step + 1) / ANALYZING_STEPS.length) * 100}%`, transition: 'width 2s ease-in-out' }} />
                    </div>
                    <p style={{ fontSize: '.85rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: 8 }}>
                        Estimated time: ~15 seconds
                    </p>
                </div>
            </div>
        </div>
    );

    return (
        <div className="page" style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', top: -100, left: '-5%', width: 500, height: 500, background: 'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />
            <Navbar />

            <div className="container" style={{ paddingTop: 40, paddingBottom: 60, position: 'relative', zIndex: 1 }}>
                <div className="page-header" style={{ animation: 'fadeInUp 0.4s ease forwards' }}>
                    <h1 className="page-title">Start New Analysis</h1>
                    <p className="page-subtitle">Upload a medical scan for instant AI processing and diagnostic report generation.</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32, alignItems: 'start' }}>
                    {/* Left: Upload + scan type */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, animation: 'fadeInUp 0.5s ease forwards', animationDelay: '0.1s', opacity: 0 }}>
                        {/* File upload */}
                        <div className="card glass-panel">
                            <h3 style={{ fontWeight: 700, marginBottom: 20, fontSize: '1.1rem' }}>Upload Medical File</h3>
                            <div {...getRootProps()} className={`dropzone${isDragActive ? ' active' : ''}`} style={{ borderColor: isDragActive ? 'var(--teal-400)' : 'var(--border)', background: isDragActive ? 'rgba(20,184,166,.05)' : 'rgba(255,255,255,.02)' }}>
                                <input {...getInputProps()} />
                                {file ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                                        <CheckCircle size={48} color="var(--green-400)" />
                                        <div style={{ fontWeight: 600, fontSize: '1.05rem', color: 'var(--text-primary)' }}>{file.name}</div>
                                        <div style={{ color: 'var(--text-secondary)', fontSize: '.9rem' }}>
                                            {(file.size / 1024 / 1024).toFixed(2)} MB · Click to choose a different file
                                        </div>
                                    </div>
                                ) : (
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                                        <UploadCloud size={56} color="var(--text-muted)" />
                                        <div>
                                            <div className="dropzone-title" style={{ fontSize: '1.15rem', color: isDragActive ? 'var(--teal-400)' : 'var(--text-primary)' }}>
                                                {isDragActive ? 'Drop file here to upload' : 'Drag & drop image or PDF here'}
                                            </div>
                                            <div className="dropzone-sub">Supported formats: JPG, PNG, WEBP, PDF (Max 20MB)</div>
                                        </div>
                                        <button className="btn btn-ghost btn-sm" style={{ marginTop: 8 }}>Browse Files</button>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Scan type */}
                        <div className="card glass-panel">
                            <h3 style={{ fontWeight: 700, marginBottom: 20, fontSize: '1.1rem' }}>Select Modality</h3>
                            <div className="scan-type-grid">
                                {SCAN_TYPES.map(t => (
                                    <button
                                        key={t.id}
                                        className={`scan-type-btn${scanType === t.id ? ' selected' : ''}`}
                                        onClick={() => setScanType(t.id)}
                                        style={{ padding: '20px 12px' }}
                                    >
                                        <div className="icon" style={{ marginBottom: 12, color: scanType === t.id ? 'var(--teal-400)' : 'var(--text-secondary)' }}>
                                            {t.icon}
                                        </div>
                                        <div className="label">{t.label}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Right: Patient info + analyze */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, animation: 'fadeInUp 0.6s ease forwards', animationDelay: '0.2s', opacity: 0 }}>
                        <div className="card glass-panel">
                            <h3 style={{ fontWeight: 700, marginBottom: 24, fontSize: '1.1rem' }}>Patient Metadata <span style={{ fontSize: '.85rem', color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span></h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                                <div className="form-group">
                                    <label className="form-label">Patient Identifier / Name</label>
                                    <input className="form-input" placeholder="e.g. John Doe or ID-1002" value={patient.name} onChange={setP('name')} />
                                </div>
                                <div className="grid-2">
                                    <div className="form-group">
                                        <label className="form-label">Age</label>
                                        <input className="form-input" type="number" placeholder="e.g. 45" min={0} max={130} value={patient.age} onChange={setP('age')} />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Gender</label>
                                        <select className="form-select" value={patient.gender} onChange={setP('gender')}>
                                            <option value="">Unspecified</option>
                                            <option value="Male">Male</option>
                                            <option value="Female">Female</option>
                                            <option value="Other">Other</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Clinical Indication / History</label>
                                    <textarea
                                        className="form-input" rows={4} placeholder="e.g. Chronic cough for 3 weeks, low grade fever, history of smoking..."
                                        value={patient.history} onChange={setP('history')}
                                        style={{ resize: 'vertical' }}
                                    />
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div style={{ background: 'rgba(239,68,68,.12)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 'var(--radius-md)', padding: '16px', color: '#f87171', fontSize: '.9rem', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                                <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: 2 }} />
                                <div>{error}</div>
                            </div>
                        )}

                        <button
                            className="btn btn-primary btn-lg"
                            style={{ width: '100%', justifyContent: 'center', height: 60, fontSize: '1.05rem', boxShadow: '0 8px 32px rgba(20,184,166,0.4)', borderRadius: 'var(--radius-md)' }}
                            onClick={handleAnalyze}
                            disabled={!file || analyzing}
                        >
                            <Brain size={20} /> Generate AI Report
                        </button>

                        <div style={{ background: 'rgba(251,191,36,.06)', border: '1px solid rgba(251,191,36,.2)', borderRadius: 'var(--radius-md)', padding: '16px', fontSize: '.85rem', color: 'var(--text-secondary)', display: 'flex', gap: 12 }}>
                            <AlertTriangle size={20} color="var(--amber-400)" style={{ flexShrink: 0 }} />
                            <div>
                                <strong style={{ color: 'var(--amber-400)' }}>Medical Disclaimer:</strong> AI analysis is intended solely to assist clinical workflows and does not replace professional medical judgment. Always review findings with a qualified radiologist or clinician.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
