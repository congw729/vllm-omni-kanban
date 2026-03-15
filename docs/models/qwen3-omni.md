# Qwen3 Omni

<p class="dashboard-intro">
This page focuses on streaming multimodal responsiveness for Qwen3 Omni across all supported hardware targets.
</p>

<label class="time-range-control" for="time-range">
  <span class="time-range-control__label">Time Window</span>
  <select id="time-range" data-time-range>
    <option value="1d">24h</option>
    <option value="7d" selected>7 days</option>
    <option value="30d">30 days</option>
  </select>
  <span class="time-range-control__hint">Switch the window for all Qwen3 Omni charts on this page.</span>
</label>

## Streaming Performance

<div class="chart-grid chart-grid--single">
<div class="chart-card">
<h4>TTFT</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen3_omni_ttft_ms"></div>
</div>
<div class="chart-card">
<h4>TPOT</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen3_omni_tpot_ms"></div>
</div>
<div class="chart-card">
<h4>TTFP</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen3_omni_ttfp_ms"></div>
</div>
<div class="chart-card">
<h4>RTF</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen3_omni_real_time_factor"></div>
</div>
<div class="chart-card">
<h4>Throughput</h4>
<div class="chart-frame" data-chart-base="../../assets/charts/qwen3_omni_throughput_tokens_per_sec"></div>
</div>
</div>
