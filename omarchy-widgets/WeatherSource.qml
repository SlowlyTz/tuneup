import QtQuick
import Quickshell
import Quickshell.Io

// The weather at the place set in Omarchy's weather panel (open-meteo.com):
// now and the next days, asked every quarter of an hour.
Item {
  id: weatherSource

  required property var service
  required property var requests

  property var place: ({ name: "", latitude: NaN, longitude: NaN })
  property var weather: null      // {temp, feels, humidity, wind, code, day, days: [{date, code, max, min}]}
  readonly property bool wanted: service.enabled("weather")

  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/settings/weather.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      var data = {}
      try { data = JSON.parse(String(text())) } catch (e) {}
      weatherSource.place = { name: String(data.name || ""), latitude: parseFloat(String(data.latitude)),
                              longitude: parseFloat(String(data.longitude)) }
      weatherSource.fetch()
    }
  }
  onWantedChanged: if (wanted) fetch()
  Timer { interval: 900000; repeat: true; running: weatherSource.wanted; onTriggered: weatherSource.fetch() }
  // After a failed request (offline, no answer): again in a minute, not only
  // in a quarter of an hour.
  Timer { id: retry; interval: 60000; onTriggered: weatherSource.fetch() }

  function fetch() {
    if (!weatherSource.wanted) return
    var place = weatherSource.place
    if (isNaN(place.latitude) || isNaN(place.longitude)) {
      if (!place.name) return
      // Only a name: find its coordinates first.
      weatherSource.requests.get("https://geocoding-api.open-meteo.com/v1/search?count=1&format=json&name=" + encodeURIComponent(place.name), function(xhr) {
        var data = weatherSource.requests.json(xhr)
        if (!data) { retry.restart(); return }
        var hit = data.results && data.results[0]
        if (!hit) return
        weatherSource.place = { name: place.name, latitude: hit.latitude, longitude: hit.longitude }
        weatherSource.fetch()
      })
      return
    }
    var url = "https://api.open-meteo.com/v1/forecast?latitude=" + place.latitude + "&longitude=" + place.longitude
      + "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day"
      + "&daily=weather_code,temperature_2m_max,temperature_2m_min&forecast_days=4&timezone=auto"
    weatherSource.requests.get(url, function(xhr) {
      var data = weatherSource.requests.json(xhr)
      if (!data || !data.current) { retry.restart(); return }
      retry.stop()
      var days = []
      var daily = data.daily || {}
      for (var i = 1; daily.time && i < daily.time.length; i++) {
        days.push({ date: daily.time[i], code: daily.weather_code[i], max: daily.temperature_2m_max[i],
                    min: daily.temperature_2m_min[i] })
      }
      weatherSource.weather = { temp: data.current.temperature_2m, feels: data.current.apparent_temperature,
                                humidity: data.current.relative_humidity_2m, wind: data.current.wind_speed_10m,
                                code: data.current.weather_code, day: data.current.is_day === 1, days: days }
    })
  }
}
