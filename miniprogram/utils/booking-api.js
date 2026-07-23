const request = require('./request')
const BOOKING_PATH = '/api/bookings'

// Keep booking requests isolated from the larger API module so page reloads
// always receive the current booking methods in WeChat DevTools.

module.exports = {
  list(status) {
    const query = status ? `?status=${encodeURIComponent(String(status))}` : ''
    return request(`${BOOKING_PATH}${query}`)
  },

  create(data) {
    return request(BOOKING_PATH, { method: 'POST', data })
  },

  confirm(id) {
    return request(`${BOOKING_PATH}/${id}/confirm`, { method: 'POST' })
  },

  cancel(id) {
    return request(`${BOOKING_PATH}/${id}/cancel`, { method: 'POST' })
  }
}
