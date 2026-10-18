import QtQuick

// Web requests of the widgets (lyrics, weather) with a time limit:
// XMLHttpRequest has none here, so one still without an answer after 15 s
// is given up (it then ends with status 0, like being offline).
Item {
  id: requests

  readonly property int limitMs: 15000
  property var open: []

  // done(xhr) once it is finished (or given up).
  function get(url, done, headers) {
    var xhr = new XMLHttpRequest()
    xhr.onreadystatechange = function() { if (xhr.readyState === XMLHttpRequest.DONE) done(xhr) }
    xhr.open("GET", url)
    for (var name in headers || {}) xhr.setRequestHeader(name, headers[name])
    xhr.send()
    requests.open = requests.open.concat([{ xhr: xhr, at: Date.now() }])
    watch.start()
  }
  // The answer as JSON, or null (failed, no answer, not JSON).
  function json(xhr) {
    if (xhr.status !== 200) return null
    try { return JSON.parse(xhr.responseText) } catch (e) { return null }
  }

  Timer {
    id: watch
    interval: 1000
    repeat: true
    onTriggered: {
      var now = Date.now()
      var waiting = []
      for (var i = 0; i < requests.open.length; i++) {
        var o = requests.open[i]
        if (o.xhr.readyState === XMLHttpRequest.DONE || o.xhr.readyState === XMLHttpRequest.UNSENT) continue
        if (now - o.at > requests.limitMs) o.xhr.abort()
        else waiting.push(o)
      }
      requests.open = waiting
      if (!waiting.length) stop()
    }
  }
}
