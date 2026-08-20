import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsCoreOption } from 'echarts/core';

export interface LineSeries {
  label: string;
  color: string;
  values: number[];
  area?: boolean;
  showValues?: boolean;
}

const AXIS_LABEL = '#93a8bd';
const AXIS_NAME = '#9db6cc';
const GRID_LINE = 'rgba(127,150,178,0.22)';
const TOOLTIP_STYLE = {
  backgroundColor: 'var(--bg-dropdown)',
  borderColor: 'var(--border-primary)',
  borderWidth: 1,
  padding: 10,
  extraCssText: 'box-shadow: none; border-radius: 8px;',
  textStyle: { color: 'var(--text-primary)', fontSize: 12, fontFamily: 'Inter, sans-serif' },
};

/** Fade a hex colour to an rgba string; non-hex colours are returned unchanged. */
function hexToRgba(color: string, alpha: number): string {
  const hex = color.replace('#', '');
  if (!/^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$/.test(hex)) return color;
  const full = hex.length === 3 ? hex.split('').map((c) => c + c).join('') : hex;
  const n = Number.parseInt(full, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

/**
 * Reusable multi-series line chart rendered with ECharts (via ngx-echarts).
 * Pass one or more `LineSeries` plus x-axis `labels`; a series flagged `area`
 * gets a gradient fill, and `showValues` labels each point.
 */
@Component({
  selector: 'app-line-chart',
  standalone: true,
  imports: [NgxEchartsDirective],
  templateUrl: './line-chart.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './line-chart.css',
})
export class LineChart {
  @Input() series: LineSeries[] = [];
  @Input() labels: string[] = [];
  @Input() xAxisTitle = '';
  @Input() yAxisTitle = '';
  /** Chart height in px (ECharts needs a definite height). */
  @Input() heightPx = 240;

  get chartOption(): EChartsCoreOption {
    return {
      color: this.series.map((s) => s.color),
      grid: { left: 6, right: 18, top: 18, bottom: this.xAxisTitle ? 40 : 26, containLabel: true },
      tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
      xAxis: {
        type: 'category',
        data: this.labels,
        boundaryGap: false,
        name: this.xAxisTitle,
        nameLocation: 'middle',
        nameGap: 28,
        nameTextStyle: { color: AXIS_NAME, fontSize: 10.5, fontWeight: 600, fontFamily: 'Poppins, sans-serif' },
        axisLine: { lineStyle: { color: GRID_LINE } },
        axisTick: { show: false },
        axisLabel: { color: AXIS_LABEL, fontSize: 9.5, fontFamily: 'Inter, sans-serif' },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: this.yAxisTitle,
        nameLocation: 'middle',
        nameGap: 38,
        nameTextStyle: { color: AXIS_NAME, fontSize: 10.5, fontWeight: 600, fontFamily: 'Poppins, sans-serif' },
        axisLine: { show: false },
        axisLabel: { color: AXIS_LABEL, fontSize: 9.5, fontFamily: 'Inter, sans-serif' },
        splitLine: { lineStyle: { color: GRID_LINE, type: 'dashed' } },
      },
      series: this.series.map((s) => ({
        name: s.label,
        type: 'line',
        data: s.values,
        smooth: false,
        symbolSize: 7,
        lineStyle: { width: 2.5, color: s.color },
        itemStyle: { color: '#131C23', borderColor: s.color, borderWidth: 2 },
        label: {
          show: !!s.showValues,
          position: 'top',
          color: '#7FC0FF',
          fontSize: 9,
          fontWeight: 600,
          fontFamily: 'Poppins, sans-serif',
        },
        ...(s.area
          ? {
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [
                    { offset: 0, color: hexToRgba(s.color, 0.32) },
                    { offset: 1, color: hexToRgba(s.color, 0) },
                  ],
                },
              },
            }
          : {}),
      })),
    } as EChartsCoreOption;
  }
}
