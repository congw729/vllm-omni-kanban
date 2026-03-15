const charts = new Map();
let resizeBound = false;

function isDashboardHome() {
  return Boolean(document.querySelector("[data-dashboard-home]"));
}

function cloneOption(option) {
  return typeof structuredClone === "function"
    ? structuredClone(option)
    : JSON.parse(JSON.stringify(option));
}

function chartPalette() {
  const styles = getComputedStyle(document.body);
  return {
    text: styles.getPropertyValue("--dashboard-chart-text").trim() || "#5b6775",
    grid: styles.getPropertyValue("--dashboard-chart-grid").trim() || "rgba(148, 163, 184, 0.18)",
    tooltipBg: styles.getPropertyValue("--dashboard-tooltip-bg").trim() || "rgba(15, 23, 42, 0.92)",
    tooltipBorder: styles.getPropertyValue("--dashboard-tooltip-border").trim() || "rgba(148, 163, 184, 0.24)",
    tooltipText: styles.getPropertyValue("--dashboard-tooltip-text").trim() || "#f8fafc",
  };
}

function patchAxis(axis, colors) {
  if (!axis) {
    return axis;
  }
  const axes = Array.isArray(axis) ? axis : [axis];
  axes.forEach((entry) => {
    entry.axisLabel = { ...(entry.axisLabel || {}), color: colors.text };
    entry.axisLine = { ...(entry.axisLine || {}), lineStyle: { color: colors.grid } };
    entry.axisTick = { ...(entry.axisTick || {}), lineStyle: { color: colors.grid } };
    if (entry.type === "value" || entry.splitLine) {
      entry.splitLine = {
        ...(entry.splitLine || {}),
        lineStyle: { color: colors.grid },
      };
    }
  });
  return axis;
}

function applyTheme(option) {
  const colors = chartPalette();
  const themed = cloneOption(option);
  themed.backgroundColor = "transparent";
  themed.textStyle = { ...(themed.textStyle || {}), color: colors.text };
  themed.tooltip = {
    ...(themed.tooltip || {}),
    backgroundColor: colors.tooltipBg,
    borderColor: colors.tooltipBorder,
    textStyle: { ...(themed.tooltip?.textStyle || {}), color: colors.tooltipText },
  };
  if (themed.legend) {
    themed.legend = { ...(themed.legend || {}), textStyle: { ...(themed.legend.textStyle || {}), color: colors.text } };
  }
  if (themed.visualMap) {
    themed.visualMap = {
      ...(themed.visualMap || {}),
      textStyle: { ...(themed.visualMap.textStyle || {}), color: colors.text },
    };
  }
  themed.xAxis = patchAxis(themed.xAxis, colors);
  themed.yAxis = patchAxis(themed.yAxis, colors);
  return themed;
}

function chartSrc(container, range) {
  if (container.dataset.chartBase) {
    const base = container.dataset.chartBase;
    return base.includes("/") ? `${base}_${range}.json` : `assets/charts/${base}_${range}.json`;
  }
  return container.dataset.chartSrc || "";
}

function selectedRange() {
  const picker = document.querySelector("[data-time-range]");
  return picker?.value || "7d";
}

async function fetchJson(src) {
  const response = await fetch(src);
  if (!response.ok) {
    throw new Error(`failed to load ${src}`);
  }
  return response.json();
}

async function loadChart(container) {
  const src = chartSrc(container, selectedRange());
  if (!src || typeof echarts === "undefined") {
    return;
  }

  try {
    const option = applyTheme(await fetchJson(src));
    const chart = charts.get(container) || echarts.init(container);
    chart.setOption(option, true);
    charts.set(container, chart);
    container.dataset.loadedSrc = src;
    container.classList.remove("chart-frame--error");
    if (!resizeBound) {
      window.addEventListener("resize", () => {
        charts.forEach((instance) => instance.resize());
      });
      resizeBound = true;
    }
  } catch (error) {
    container.classList.add("chart-frame--error");
    container.innerHTML = `<pre>${error.message}</pre>`;
  }
}

async function reloadCharts() {
  const containers = [...document.querySelectorAll("[data-chart-src], [data-chart-base]")];
  await Promise.all(containers.map((container) => loadChart(container)));
}

function escapeHtml(text) {
  if (typeof text !== "string") {
    return "";
  }
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatPercent(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "--";
}

function formatLatency(value) {
  return typeof value === "number" ? `${value.toFixed(1)} ms` : "--";
}

function railNav() {
  return document.querySelector(".md-sidebar--secondary .md-nav--secondary");
}

function railLinkMap() {
  return new Map(
    [...document.querySelectorAll(".md-sidebar--secondary .md-nav--secondary .md-nav__link[href^='#']")]
      .map((link) => [link.getAttribute("href"), link]),
  );
}

function ensureTechnicalRail() {
  if (!isDashboardHome()) {
    return;
  }
  document.body.classList.add("dashboard-home");
  const nav = railNav();
  if (!nav || nav.dataset.technicalRail === "true") {
    return;
  }

  const title = nav.querySelector(".md-nav__title");
  if (title) {
    title.innerHTML = [
      '<span class="technical-rail__eyebrow">In This Snapshot</span>',
      '<span class="technical-rail__snapshot" data-technical-rail-title>Snapshot pending</span>',
    ].join("");
  }

  const track = document.createElement("div");
  track.className = "technical-rail__track";
  const indicator = document.createElement("div");
  indicator.className = "technical-rail__indicator";
  nav.append(track, indicator);

  railLinkMap().forEach((link) => {
    if (link.dataset.technicalRail === "true") {
      return;
    }
    const labelText = link.textContent.trim();
    link.dataset.technicalRail = "true";
    link.textContent = "";

    const content = document.createElement("span");
    content.className = "technical-rail__content";
    const dot = document.createElement("span");
    dot.className = "technical-rail__dot";
    const label = document.createElement("span");
    label.className = "technical-rail__label";
    label.textContent = labelText;
    const badge = document.createElement("span");
    badge.className = "technical-rail__badge";
    badge.hidden = true;

    content.append(dot, label);
    link.append(content, badge);
  });

  nav.dataset.technicalRail = "true";
}

function setRailStatus(hash, status, badgeText = "") {
  const link = railLinkMap().get(hash);
  if (!link) {
    return;
  }

  const dot = link.querySelector(".technical-rail__dot");
  const badge = link.querySelector(".technical-rail__badge");
  if (dot) {
    dot.className = `technical-rail__dot technical-rail__dot--${status}`;
  }
  if (badge) {
    badge.hidden = !badgeText;
    badge.textContent = badgeText;
  }
}

function updateRailSummary(summary) {
  if (!isDashboardHome()) {
    return;
  }
  const title = document.querySelector("[data-technical-rail-title]");
  if (title) {
    title.textContent = summary.latest_date ? `Snapshot: ${summary.latest_date}` : "Snapshot unavailable";
  }

  const performanceStatus = typeof summary.overall_pass_rate === "number"
    ? (summary.overall_pass_rate >= 0.9 ? "healthy" : summary.overall_pass_rate >= 0.8 ? "warning" : "critical")
    : "unknown";
  const alertStatus = summary.recent_alerts
    ? (summary.critical_alerts ? "critical" : "warning")
    : "healthy";

  setRailStatus("#model-performance", performanceStatus);
  setRailStatus("#pass-rate", alertStatus);
  setRailStatus("#recent-alerts", alertStatus, summary.recent_alerts ? String(summary.recent_alerts) : "");
  setRailStatus("#reports", summary.latest_date ? "healthy" : "unknown");
}

function updateRailIndicator() {
  const nav = railNav();
  const indicator = nav?.querySelector(".technical-rail__indicator");
  const active = nav?.querySelector(".technical-rail__link--active");
  if (!nav || !indicator || !active) {
    return;
  }
  indicator.style.opacity = "1";
  indicator.style.transform = `translateY(${active.offsetTop}px)`;
  indicator.style.height = `${active.offsetHeight}px`;
}

function renderRailModelNodes() {
  if (!isDashboardHome()) {
    return;
  }
  const modelLink = railLinkMap().get("#model-performance");
  const modelItem = modelLink?.closest(".md-nav__item");
  if (!modelItem) {
    return;
  }

  const models = [...document.querySelectorAll("[data-model-anchor]")]
    .map((section) => {
      const heading = section.querySelector("h3");
      return heading ? { id: section.id, label: heading.textContent.trim() } : null;
    })
    .filter(Boolean);
  if (models.length === 0) {
    return;
  }

  const sublist = modelItem.querySelector(".technical-rail__sublist") || document.createElement("ul");
  sublist.className = "technical-rail__sublist";
  sublist.innerHTML = models
    .map((model) => `
      <li class="technical-rail__subitem">
        <a href="#${model.id}" class="technical-rail__sublink" data-model-link="${model.id}">${escapeHtml(model.label)}</a>
      </li>
    `)
    .join("");

  if (!sublist.parentElement) {
    modelItem.append(sublist);
  }
}

function bindRailSpy() {
  if (!isDashboardHome()) {
    return;
  }
  const links = [...railLinkMap().values()];
  const sections = links
    .map((link) => ({ link, section: document.querySelector(link.getAttribute("href")) }))
    .filter((entry) => entry.section);
  if (sections.length === 0) {
    return;
  }

  const refreshActive = () => {
    let current = sections[0];
    sections.forEach((entry) => {
      if (entry.section.getBoundingClientRect().top <= 140) {
        current = entry;
      }
    });
    sections.forEach(({ link }) => {
      link.classList.toggle("technical-rail__link--active", link === current.link);
    });

    const modelLinks = [...document.querySelectorAll(".technical-rail__sublink[data-model-link]")];
    if (current.link.getAttribute("href") === "#model-performance" && modelLinks.length) {
      const threshold = 180;
      let currentModel = modelLinks[0];
      modelLinks.forEach((link) => {
        const section = document.getElementById(link.dataset.modelLink);
        if (section && section.getBoundingClientRect().top <= threshold) {
          currentModel = link;
        }
      });
      modelLinks.forEach((link) => {
        link.classList.toggle("technical-rail__sublink--active", link === currentModel);
      });
    } else {
      modelLinks.forEach((link) => link.classList.remove("technical-rail__sublink--active"));
    }

    updateRailIndicator();
  };

  window.addEventListener("scroll", refreshActive, { passive: true });
  window.addEventListener("resize", refreshActive);
  links.forEach((link) => {
    link.addEventListener("click", () => window.setTimeout(refreshActive, 80));
  });
  refreshActive();
}

function renderHealth(summary) {
  const banner = document.querySelector("[data-summary-src]");
  if (!banner) {
    return;
  }

  const alerts = summary.recent_alerts || 0;
  const warningAlerts = summary.warning_alerts || 0;
  const criticalAlerts = summary.critical_alerts || 0;
  const healthy = alerts === 0;
  const title = banner.querySelector("[data-health-title]");
  const meta = banner.querySelector("[data-health-meta]");

  banner.classList.toggle("health-banner--healthy", healthy);
  banner.classList.toggle("health-banner--alert", !healthy);
  if (title) {
    title.textContent = healthy ? "All systems normal" : `${alerts} alerts firing`;
  }
  if (meta) {
    meta.textContent = healthy
      ? `Latest snapshot ${summary.latest_date || "--"} · pass rate ${formatPercent(summary.overall_pass_rate)} · latency ${formatLatency(summary.overall_latency_p99_ms)}`
      : `${criticalAlerts} critical · ${warningAlerts} warning · latest snapshot ${summary.latest_date || "--"}`;
  }
  updateRailSummary(summary);
}

async function loadHealth() {
  const banner = document.querySelector("[data-summary-src]");
  if (!banner) {
    return;
  }

  try {
    renderHealth(await fetchJson(banner.dataset.summarySrc));
  } catch (error) {
    const title = banner.querySelector("[data-health-title]");
    const meta = banner.querySelector("[data-health-meta]");
    banner.classList.add("health-banner--alert");
    if (title) {
      title.textContent = "Health summary unavailable";
    }
    if (meta) {
      meta.textContent = error.message;
    }
  }
}

function renderHardwareStatus(data) {
  const container = document.querySelector("[data-hardware-status-src]");
  if (!container) {
    return;
  }

  const hardwareList = data.hardware || [];
  if (hardwareList.length === 0) {
    container.innerHTML = '<p class="hardware-status-empty">No hardware status available</p>';
    return;
  }

  const statusIcons = {
    healthy: "✅",
    warning: "⚠️",
    critical: "❌",
    unknown: "❓",
  };

  const html = hardwareList
    .map((hw) => {
      const icon = statusIcons[hw.status] || statusIcons.unknown;
      const passRateText = typeof hw.pass_rate === "number" ? formatPercent(hw.pass_rate) : "--";
      const latencyText = typeof hw.latency_p99_ms === "number" ? formatLatency(hw.latency_p99_ms) : "--";
      return `
        <div class="hardware-status-card hardware-status-card--${escapeHtml(hw.status)}">
          <span class="hardware-status-icon">${icon}</span>
          <span class="hardware-status-name">${escapeHtml(hw.display_name)}</span>
          <span class="hardware-status-pass">${passRateText}</span>
          <span class="hardware-status-latency">${latencyText}</span>
        </div>
      `;
    })
    .join("");

  container.innerHTML = `<div class="hardware-status-grid">${html}</div>`;
}

async function loadHardwareStatus() {
  const container = document.querySelector("[data-hardware-status-src]");
  if (!container) {
    return;
  }

  try {
    renderHardwareStatus(await fetchJson(container.dataset.hardwareStatusSrc));
  } catch (error) {
    container.innerHTML = `<p class="hardware-status-error">Failed to load hardware status: ${error.message}</p>`;
  }
}

function bindRangePicker() {
  const picker = document.querySelector("[data-time-range]");
  if (!picker) {
    return;
  }
  picker.addEventListener("change", async () => {
    await reloadCharts();
  });
}

function observeColorScheme() {
  const target = document.body;
  if (!target) {
    return;
  }
  const observer = new MutationObserver(() => {
    reloadCharts();
  });
  observer.observe(target, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
}

document.addEventListener("DOMContentLoaded", async () => {
  ensureTechnicalRail();
  renderRailModelNodes();
  bindRangePicker();
  bindRailSpy();
  observeColorScheme();
  await Promise.all([loadHealth(), loadHardwareStatus(), reloadCharts()]);
});
