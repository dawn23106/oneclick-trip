const LOCAL_ASSETS = {
  'travel-hero-v2.png': '/assets/travel/travel-hero.jpg',
  'travel-hero-ai.png': '/assets/travel/travel-hero.jpg',
  'chengdu-destination.png': '/assets/travel/chengdu.jpg',
  'hangzhou-west-lake.png': '/assets/travel/hangzhou.jpg',
  'xian-city-wall.png': '/assets/travel/xian.jpg',
  'dali-erhai.png': '/assets/travel/dali.jpg'
}

const CITY_ASSETS = [
  { id: 1, matches: ['成都', 'chengdu'], path: '/assets/travel/chengdu.jpg' },
  { id: 2, matches: ['杭州', 'hangzhou'], path: '/assets/travel/hangzhou.jpg' },
  { id: 3, matches: ['西安', 'xian'], path: '/assets/travel/xian.jpg' },
  { id: 4, matches: ['大理', 'dali'], path: '/assets/travel/dali.jpg' }
]

function resolveTravelImage(value, hint) {
  const url = String(value || '').trim()
  if (/^https?:\/\//i.test(url)) return url

  const fileName = url.replace(/\\/g, '/').split('/').pop().toLowerCase()
  if (LOCAL_ASSETS[fileName]) return LOCAL_ASSETS[fileName]
  return resolveCityImage(`${url} ${hint || ''}`)
}

function resolveCityImage(cityName, cityId) {
  const numericId = Number(cityId)
  if (numericId >= 1 && numericId <= CITY_ASSETS.length) {
    return CITY_ASSETS[numericId - 1].path
  }
  const searchText = String(cityName || '').toLowerCase()
  for (let index = 0; index < CITY_ASSETS.length; index += 1) {
    const city = CITY_ASSETS[index]
    for (let tokenIndex = 0; tokenIndex < city.matches.length; tokenIndex += 1) {
      if (searchText.indexOf(city.matches[tokenIndex]) >= 0) return city.path
    }
  }
  return ''
}

module.exports = {
  heroImage: '/assets/travel/travel-hero.jpg',
  resolveTravelImage,
  resolveCityImage
}
