// Page header: title + subtitle on the left, date (two lines) and the localhost pill on the right.
import { h, icon } from "../dom.js";
import { fmtDateLong, weekday } from "../format.js";
import { getSession } from "../api.js";

export function PageHeader(title, subtitle) {
  const now = sessionDate();
  return h("header", { class: "page-head" },
    h("div", {}, h("h1", { class: "t-page" }, title), h("p", { class: "page-sub" }, subtitle)),
    h("div", { class: "page-head-right" },
      h("div", { class: "page-date" }, icon("calendar"), h("div", {}, h("b", {}, fmtDateLong(now)), h("span", {}, weekday(now)))),
      h("div", { class: "page-host" }, h("span", { class: "dot green", style: { width: "10px", height: "10px" } }), h("span", {}, getSession()?.server || "localhost:8787"))));
}

function sessionDate() {
  const session = getSession();
  if (session?.now) {
    // The server sends its own clock (with timezone); render that day, not the browser's guess.
    const d = new Date(session.now);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return new Date();
}
