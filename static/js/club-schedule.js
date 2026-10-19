(function () {
  var WEEKDAYS = {
    sunday: 0,
    monday: 1,
    tuesday: 2,
    wednesday: 3,
    thursday: 4,
    friday: 5,
    saturday: 6,
  };
  var WEEKDAY_SHORT = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  var PL = [
    null,
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "września",
    "października",
    "listopada",
    "grudnia",
  ];
  var EN_LONG = [
    null,
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  var EN_N = [
    null,
    "Jan.",
    "Feb.",
    "March",
    "April",
    "May",
    "June",
    "July",
    "Aug.",
    "Sept.",
    "Oct.",
    "Nov.",
    "Dec.",
  ];

  function warsawParts(date) {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Europe/Warsaw",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "short",
    }).formatToParts(date);
    function get(type) {
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].type === type) return parts[i].value;
      }
    }
    return {
      year: +get("year"),
      month: +get("month"),
      day: +get("day"),
      weekday: WEEKDAY_SHORT[get("weekday")],
    };
  }

  function addDays(year, month, day, days) {
    var utc = new Date(Date.UTC(year, month - 1, day + days));
    return {
      year: utc.getUTCFullYear(),
      month: utc.getUTCMonth() + 1,
      day: utc.getUTCDate(),
    };
  }

  function iso(date) {
    var month = date.month < 10 ? "0" + date.month : String(date.month);
    var day = date.day < 10 ? "0" + date.day : String(date.day);
    return date.year + "-" + month + "-" + day;
  }

  function formatDate(date, lang, style) {
    if (lang === "pl") return date.day + " " + PL[date.month] + " " + date.year;
    var months = style === "long" ? EN_LONG : EN_N;
    return months[date.month] + " " + date.day + ", " + date.year;
  }

  function apply(config) {
    var target = WEEKDAYS[config.weekday];
    if (target === undefined) return;
    var today = warsawParts(new Date());
    var delta = (target - today.weekday + 7) % 7;
    var next = addDays(today.year, today.month, today.day, delta);
    var lang = document.documentElement.lang || "pl";
    var nodes = document.querySelectorAll("[data-next-meeting-date]");
    for (var i = 0; i < nodes.length; i++) {
      var style = nodes[i].getAttribute("data-date-style") || "event";
      nodes[i].textContent = formatDate(next, lang, style);
    }
    var todayIso = iso(today);
    var cards = document.querySelectorAll("[data-hide-after]");
    for (var j = 0; j < cards.length; j++) {
      var until = cards[j].getAttribute("data-hide-after");
      if (until && todayIso > until) cards[j].remove();
    }
  }

  fetch("/config/club.json", { cache: "no-cache" })
    .then(function (response) {
      if (!response.ok) throw new Error("config");
      return response.json();
    })
    .then(apply)
    .catch(function () {});
})();
