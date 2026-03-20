const charts = new Map();
let resizeBound = false;

function isDashboardHome() {
  return Boolean(document.querySelector("[data-dashboard-home]"));
}

function cloneOption(option) {
  if (Array.isArray(option)) {
    return option.map((item) => cloneOption(item));
  }
  if (option && typeof option === "object") {
    const cloned = {};
    Object.entries(option).forEach(([key, value]) => {
      cloned[key] = cloneOption(value);
    });
    return cloned;
  }
  return option;
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

function isNumeric(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function formatMetricValue(value, digits = 4) {
  return isNumeric(value) ? value.toFixed(digits) : "--";
}

function formatTableValue(field, value) {
  if (field === "model_id" || field === "tokenizer_id") {
    return escapeHtml(String(value || "--"));
  }
  if (isNumeric(value)) {
    return value.toFixed(4);
  }
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return escapeHtml(String(value));
}

function humanizeToken(value) {
  const mapping = {
    ttft: "TTFT",
    tpot: "TPOT",
    ttfp: "TTFP",
    itl: "ITL",
    e2el: "E2EL",
    rtf: "RTF",
  };
  return mapping[value.toLowerCase()] || `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function humanizeField(field) {
  return field
    .split("_")
    .map((part) => humanizeToken(part))
    .join(" ");
}

function disposeChartsWithin(root) {
  [...charts.entries()].forEach(([container, chart]) => {
    if (root.contains(container)) {
      chart.dispose();
      charts.delete(container);
    }
  });
}

function setChart(container, option) {
  if (typeof echarts === "undefined") {
    return;
  }
  const chart = charts.get(container) || echarts.init(container);
  chart.setOption(applyTheme(option), true);
  charts.set(container, chart);
}

function buildSeriesLabel(record) {
  return [
    record.test_name,
    record.dataset_name || "dataset:n/a",
    `mc=${record.max_concurrency}`,
    `np=${record.num_prompts}`,
  ].join(" · ");
}

function filterRecords(records, filters) {
  return records.filter((record) => Object.entries(filters).every(([field, value]) => {
    if (!value) {
      return true;
    }
    const raw = record[field];
    if (raw === null || raw === undefined) {
      return false;
    }
    if (typeof raw === "number") {
      return String(raw) === value.trim();
    }
    return String(raw).toLowerCase().includes(value.trim().toLowerCase());
  }));
}

function groupRecords(records, fields) {
  const grouped = new Map();
  records.forEach((record) => {
    const key = fields.map((field) => record[field]).join("||");
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key).push(record);
  });
  return grouped;
}

function buildOmniMetricSeries(records, metric, groupFields) {
  const grouped = groupRecords(records, groupFields);
  const series = [];
  grouped.forEach((items) => {
    const points = items
      .filter((item) => isNumeric(item[metric]))
      .sort((left, right) => left.sort_timestamp.localeCompare(right.sort_timestamp))
      .map((item) => ({
        value: [item.date, item[metric]],
        meta: {
          test_name: item.test_name,
          dataset_name: item.dataset_name,
          max_concurrency: item.max_concurrency,
          num_prompts: item.num_prompts,
          metric,
          source_file: item.source_file,
        },
      }));
    if (points.length > 0) {
      series.push({
        name: `${buildSeriesLabel(items[0])} · ${humanizeField(metric)}`,
        type: "line",
        showSymbol: points.length < 8,
        smooth: false,
        data: points,
      });
    }
  });
  return series;
}

function buildOmniChartOption(metricGroup, records, groupFields) {
  const series = metricGroup.metrics.flatMap((metric) => buildOmniMetricSeries(records, metric, groupFields));
  return {
    tooltip: {
      trigger: "item",
      formatter(params) {
        const meta = params.data?.meta || {};
        return [
          `<strong>${escapeHtml(params.seriesName || "")}</strong>`,
          escapeHtml(String(params.data?.value?.[0] || "")),
          `Value: ${formatMetricValue(params.data?.value?.[1])}`,
          `Test: ${escapeHtml(meta.test_name || "--")}`,
          `Dataset: ${escapeHtml(meta.dataset_name || "--")}`,
          `Max concurrency: ${escapeHtml(String(meta.max_concurrency ?? "--"))}`,
          `Num prompts: ${escapeHtml(String(meta.num_prompts ?? "--"))}`,
        ].join("<br>");
      },
    },
    legend: {
      type: "scroll",
      top: 0,
      textStyle: { fontSize: 11 },
    },
    grid: {
      left: 56,
      right: 24,
      top: 60,
      bottom: 24,
      containLabel: true,
    },
    xAxis: {
      type: "time",
      axisLabel: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter(value) {
          return Number(value).toFixed(2);
        },
      },
    },
    series,
  };
}

function renderOmniFilterBar(payload, filters) {
  const container = document.querySelector("[data-omni-history-filters]");
  if (!container) {
    return;
  }
  container.innerHTML = payload.filters.map((field) => {
    const datalistId = `omni-filter-${field}`;
    const options = (payload.filter_options?.[field] || [])
      .map((option) => `<option value="${escapeHtml(String(option))}"></option>`)
      .join("");
    return `
      <label class="omni-filter">
        <span class="omni-filter__label">${escapeHtml(humanizeField(field))}</span>
        <input
          class="omni-filter__input"
          type="text"
          list="${datalistId}"
          data-omni-filter="${field}"
          value="${escapeHtml(filters[field] || "")}"
          placeholder="All"
        >
        <datalist id="${datalistId}">${options}</datalist>
      </label>
    `;
  }).join("") + `
    <button type="button" class="omni-filter__reset" data-omni-filter-reset>Reset filters</button>
  `;

  container.querySelectorAll("[data-omni-filter]").forEach((input) => {
    input.addEventListener("input", () => {
      renderQwen3OmniHistory(payload);
    });
  });
  container.querySelector("[data-omni-filter-reset]")?.addEventListener("click", () => {
    container.querySelectorAll("[data-omni-filter]").forEach((input) => {
      input.value = "";
    });
    renderQwen3OmniHistory(payload);
  });
}

function currentOmniFilters(payload) {
  const inputs = [...document.querySelectorAll("[data-omni-filter]")];
  return payload.filters.reduce((acc, field) => {
    const input = inputs.find((item) => item.dataset.omniFilter === field);
    acc[field] = input?.value?.trim() || "";
    return acc;
  }, {});
}

function renderOmniSummary(records, groupFields) {
  const container = document.querySelector("[data-omni-history-summary]");
  if (!container) {
    return;
  }
  const latest = records[0];
  const configs = groupRecords(records, groupFields).size;
  container.innerHTML = `
    <div class="omni-summary-card">
      <span class="omni-summary-card__eyebrow">Visible Records</span>
      <strong class="omni-summary-card__value">${records.length}</strong>
    </div>
    <div class="omni-summary-card">
      <span class="omni-summary-card__eyebrow">Visible Configs</span>
      <strong class="omni-summary-card__value">${configs}</strong>
    </div>
    <div class="omni-summary-card">
      <span class="omni-summary-card__eyebrow">Latest Result</span>
      <strong class="omni-summary-card__value">${escapeHtml(latest?.date || "--")}</strong>
    </div>
  `;
}

function renderOmniTable(payload, records) {
  const container = document.querySelector("[data-omni-history-table]");
  if (!container) {
    return;
  }
  if (records.length === 0) {
    container.innerHTML = '<div class="omni-empty-state">当前筛选条件下没有数据。</div>';
    return;
  }

  const header = payload.table_columns
    .map((field) => `<th scope="col">${escapeHtml(humanizeField(field))}</th>`)
    .join("");
  const body = records.map((record) => {
    const cells = payload.table_columns.map((field) => {
      const numericClass = isNumeric(record[field]) ? " omni-history-table__cell--numeric" : "";
      return `<td class="omni-history-table__cell${numericClass}">${formatTableValue(field, record[field])}</td>`;
    }).join("");
    return `<tr>${cells}</tr>`;
  }).join("");

  container.innerHTML = `
    <div class="omni-history-table__wrap">
      <table class="omni-history-table">
        <thead><tr>${header}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function renderOmniSnapshot(metricGroup, records, groupFields) {
  const seriesByMetric = metricGroup.metrics.flatMap((metric) => buildOmniMetricSeries(records, metric, groupFields));
  const items = seriesByMetric
    .map((series) => {
      const point = series.data[series.data.length - 1];
      return point ? `
        <div class="omni-snapshot-card">
          <span class="omni-snapshot-card__name">${escapeHtml(series.name)}</span>
          <strong class="omni-snapshot-card__value">${formatMetricValue(point.value[1])}</strong>
          <span class="omni-snapshot-card__meta">${escapeHtml(String(point.value[0]))}</span>
        </div>
      ` : "";
    })
    .filter(Boolean)
    .join("");
  return items || '<div class="omni-empty-state">当前分组没有可展示的数值。</div>';
}

function renderOmniChartSection(section, metricGroup, records, groupFields) {
  const chartRoot = document.createElement("section");
  chartRoot.className = "omni-chart-card";
  const allSeries = metricGroup.metrics.flatMap((metric) => buildOmniMetricSeries(records, metric, groupFields));
  const pointCount = allSeries.reduce((maxCount, series) => Math.max(maxCount, series.data.length), 0);

  chartRoot.innerHTML = `
    <div class="omni-chart-card__header">
      <div>
        <h3>${escapeHtml(metricGroup.title)}</h3>
        <p>${metricGroup.metrics.map(humanizeField).join(" · ")}</p>
      </div>
      <span class="omni-chart-card__badge">${allSeries.length} series</span>
    </div>
  `;

  if (allSeries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "omni-empty-state";
    empty.textContent = "当前筛选条件下没有数据。";
    chartRoot.append(empty);
    section.append(chartRoot);
    return;
  }

  if (pointCount < 2) {
    const snapshot = document.createElement("div");
    snapshot.className = "omni-snapshot-grid";
    snapshot.innerHTML = renderOmniSnapshot(metricGroup, records, groupFields);
    chartRoot.append(snapshot);
    section.append(chartRoot);
    return;
  }

  const chart = document.createElement("div");
  chart.className = "chart-frame omni-chart-frame";
  chartRoot.append(chart);
  section.append(chartRoot);
  setChart(chart, buildOmniChartOption(metricGroup, records, groupFields));
}

function renderOmniCharts(payload, records) {
  const container = document.querySelector("[data-omni-history-charts]");
  if (!container) {
    return;
  }
  disposeChartsWithin(container);
  container.innerHTML = "";

  const primary = document.createElement("div");
  primary.className = "omni-chart-grid";
  container.append(primary);
  payload.metric_groups.slice(0, 3).forEach((metricGroup) => {
    renderOmniChartSection(primary, metricGroup, records, payload.group_fields);
  });

  if (payload.metric_groups.length > 3) {
    const details = document.createElement("details");
    details.className = "omni-more-charts";
    details.innerHTML = '<summary>More charts</summary>';
    const extra = document.createElement("div");
    extra.className = "omni-chart-grid omni-chart-grid--stacked";
    details.append(extra);
    container.append(details);
    let extraRendered = false;
    const renderExtraCharts = () => {
      if (extraRendered) {
        return;
      }
      payload.metric_groups.slice(3).forEach((metricGroup) => {
        renderOmniChartSection(extra, metricGroup, records, payload.group_fields);
      });
      extraRendered = true;
    };
    details.addEventListener("toggle", () => {
      if (details.open) {
        renderExtraCharts();
      }
    });
  }
}

function renderQwen3OmniHistory(payload) {
  const filters = currentOmniFilters(payload);
  renderOmniFilterBar(payload, filters);
  const filtered = filterRecords(payload.records, filters);
  renderOmniSummary(filtered, payload.group_fields);
  renderOmniCharts(payload, filtered);
  renderOmniTable(payload, filtered);
}

async function loadQwen3OmniHistory() {
  const root = document.querySelector("[data-omni-history-src]");
  if (!root) {
    return;
  }

  try {
    const payload = await fetchJson(root.dataset.omniHistorySrc);
    renderQwen3OmniHistory(payload);
  } catch (error) {
    root.innerHTML = `<div class="omni-empty-state">Failed to load Qwen3 Omni history: ${escapeHtml(error.message)}</div>`;
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
  await Promise.all([loadHealth(), loadHardwareStatus(), reloadCharts(), loadQwen3OmniHistory()]);
});
