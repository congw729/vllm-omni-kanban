# Qwen Image

<p class="dashboard-intro">
This page focuses on end-to-end generation cost for Qwen Image, with the main view centered on latency and memory pressure across hardware.
</p>

<label class="time-range-control" for="time-range">
  <span class="time-range-control__label">Time Window</span>
  <select id="time-range" data-time-range>
    <option value="1d">24h</option>
    <option value="7d" selected>7 days</option>
    <option value="30d">30 days</option>
  </select>
  <span class="time-range-control__hint">Switch the window for all Qwen Image charts on this page.</span>
</label>

## Generation Cost

<div class="chart-grid chart-grid--single">
<div class="chart-card">
<h4>E2E Latency</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen_image_e2e_latency_ms"></div>
</div>
<div class="chart-card">
<h4>Peak Memory</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen_image_peak_memory_gb"></div>
</div>
</div>
