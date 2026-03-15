# WAN 2.2

<p class="dashboard-intro">
This page tracks video-generation cost for WAN 2.2, with dedicated visibility into full request latency and peak memory usage per hardware target.
</p>

<label class="time-range-control" for="time-range">
  <span class="time-range-control__label">Time Window</span>
  <select id="time-range" data-time-range>
    <option value="1d">24h</option>
    <option value="7d" selected>7 days</option>
    <option value="30d">30 days</option>
  </select>
  <span class="time-range-control__hint">Switch the window for all WAN 2.2 charts on this page.</span>
</label>

## Generation Cost

<div class="chart-grid chart-grid--single">
<div class="chart-card">
<h4>E2E Latency</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/wan22_e2e_latency_ms"></div>
</div>
<div class="chart-card">
<h4>Peak Memory</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/wan22_peak_memory_gb"></div>
</div>
</div>
