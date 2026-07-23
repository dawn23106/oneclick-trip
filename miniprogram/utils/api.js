const request = require('./request')

module.exports = {
  login: data => request('/api/auth/login', { method: 'POST', data }),
  register: data => request('/api/auth/register', { method: 'POST', data }),
  me: () => request('/api/users/me'),
  updateProfile: data => request('/api/users/me', { method: 'PUT', data }),
  cities: () => request('/api/cities'),
  city: id => request(`/api/cities/${id}`),
  spots: id => request(`/api/cities/${id}/spots`),
  foods: id => request(`/api/cities/${id}/foods`),
  hotels: id => request(`/api/cities/${id}/hotels`),
  templates: cityId => request(`/api/trip-templates${cityId ? `?cityId=${cityId}` : ''}`),
  tripPlans: () => request('/api/trip-plans'),
  tripPlan: id => request(`/api/trip-plans/${id}`),
  aiTripPlan: id => request(`/api/trip-plans/ai/${id}`),
  conversations: () => request('/api/ai/conversations'),
  createConversation: title => request('/api/ai/conversations', { method: 'POST', data: { title: title || '' } }),
  conversation: id => request(`/api/ai/conversations/${id}`),
  deleteConversation: id => request(`/api/ai/conversations/${id}`, { method: 'DELETE' }),
  startChat: data => request('/api/ai/chat/async', { method: 'POST', data }),
  aiJob: id => request(`/api/ai/jobs/${id}`),
  resume: data => request('/api/ai/resume', { method: 'POST', data })
}
