-- MediVision AI — Supabase Schema
-- Run this in Supabase SQL Editor to set up your database

-- Analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    scan_type TEXT NOT NULL,
    filename TEXT,
    patient_name TEXT DEFAULT 'Anonymous',
    patient_age INTEGER,
    patient_gender TEXT,
    clinical_history TEXT,
    findings JSONB DEFAULT '[]',
    impression TEXT,
    differentials JSONB DEFAULT '[]',
    urgency TEXT DEFAULT 'ROUTINE',
    recommendations JSONB DEFAULT '[]',
    confidence INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast user history queries
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_scan_type ON analyses(scan_type);

-- Row Level Security
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see their own analyses
CREATE POLICY "Users can read own analyses" ON analyses
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analyses" ON analyses
    FOR INSERT WITH CHECK (auth.uid() = user_id);
