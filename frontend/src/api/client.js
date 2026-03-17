import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_URL,
  timeout: 120000, // 2 minutes for large file analysis
});

export async function analyzeFile({ file, scanType, patientName, patientAge, patientGender, clinicalHistory, userId }) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('scan_type', scanType);
  if (patientName) formData.append('patient_name', patientName);
  if (patientAge) formData.append('patient_age', patientAge);
  if (patientGender) formData.append('patient_gender', patientGender);
  if (clinicalHistory) formData.append('clinical_history', clinicalHistory);
  if (userId) formData.append('user_id', userId);

  const response = await client.post('/api/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

export async function getAnalysis(id, userId) {
  const response = await client.get(`/api/analyses/${id}`, { params: { user_id: userId } });
  return response.data;
}

export async function getHistory({ userId, page = 1, limit = 20, scanType }) {
  const params = { user_id: userId, page, limit };
  if (scanType) params.scan_type = scanType;
  const response = await client.get('/api/history', { params });
  return response.data;
}

export async function getDashboardStats(userId) {
  const response = await client.get('/api/dashboard/stats', { params: { user_id: userId } });
  return response.data;
}

export default client;
