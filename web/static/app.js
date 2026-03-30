(function () {
  let chart;
  let table;

  function fmtMeta(meta) {
    if (!meta) return "";
    return `조회: ${meta.dataDateStart} ~ ${meta.dataDateEnd} · 출처: ${meta.source}`;
  }

  function buildChart(daily) {
    const labels = daily.map((d) => d.date);
    const ds = (field) => daily.map((d) => d[field]);

    const chartData = {
      labels,
      datasets: [
        {
          label: "살 때 순금",
          data: ds("s_pure"),
          borderColor: "#f2c14e",
          backgroundColor: "rgba(242, 193, 78, 0.08)",
          tension: 0.2,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "팔 때 순금",
          data: ds("p_pure"),
          borderColor: "#6ee7b7",
          backgroundColor: "rgba(110, 231, 183, 0.06)",
          tension: 0.2,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "팔 때 18K",
          data: ds("p_18k"),
          borderColor: "#60a5fa",
          backgroundColor: "rgba(96, 165, 250, 0.06)",
          tension: 0.2,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "팔 때 14K",
          data: ds("p_14k"),
          borderColor: "#c084fc",
          backgroundColor: "rgba(192, 132, 252, 0.06)",
          tension: 0.2,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    };

    const ctx = document.getElementById("priceChart");
    if (chart) {
      chart.destroy();
    }
    chart = new Chart(ctx, {
      type: "line",
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = ctx.parsed.y;
                if (v == null) return ctx.dataset.label;
                return `${ctx.dataset.label}: ${v.toLocaleString("ko-KR")}원`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(255,255,255,0.06)" },
            ticks: {
              color: "#8b98a8",
              maxRotation: 45,
              autoSkip: true,
              maxTicksLimit: 14,
            },
          },
          y: {
            grid: { color: "rgba(255,255,255,0.06)" },
            ticks: {
              color: "#8b98a8",
              callback: (v) => v.toLocaleString("ko-KR"),
            },
          },
        },
      },
    });
  }

  function wireLegendToggles() {
    document.querySelectorAll(".legend-toggles input[data-series]").forEach((el) => {
      el.addEventListener("change", () => {
        const idx = Number(el.getAttribute("data-series"), 10);
        if (!chart || !chart.data.datasets[idx]) return;
        const vis = el.checked;
        chart.setDatasetVisibility(idx, vis);
        chart.update();
      });
    });
  }

  function columnMinMax(rows, field) {
    const nums = rows
      .map((r) => r[field])
      .filter((v) => typeof v === "number" && !Number.isNaN(v));
    if (!nums.length) return { min: null, max: null };
    return { min: Math.min(...nums), max: Math.max(...nums) };
  }

  function formatMoneyKo(n) {
    return Number(n).toLocaleString("ko-KR");
  }

  function priceCellFormatter(stats) {
    return function (cell) {
      const v = cell.getValue();
      if (v == null || v === "") return "";
      const num = Number(v);
      if (Number.isNaN(num)) return "";
      const text = formatMoneyKo(num);
      let color = "#ffffff";
      if (stats.max != null && num === stats.max) {
        color = "#f87171";
      } else if (stats.min != null && num === stats.min) {
        color = "#60a5fa";
      }
      return `<span class="price-cell" style="color:${color}">${text}</span>`;
    };
  }

  function buildTable(rows) {
    if (table) {
      table.destroy();
    }
    const priceFields = ["s_pure", "p_pure", "p_18k", "p_14k"];
    const statsByField = Object.fromEntries(
      priceFields.map((f) => [f, columnMinMax(rows, f)])
    );

    table = new Tabulator("#example-table", {
      layout: "fitColumns",
      data: rows,
      pagination: "local",
      paginationSize: 15,
      paginationButtonCount: 8,
      placeholder: "데이터가 없습니다.",
      headerSort: false,
      height: "420px",
      columns: [
        {
          title: "고시일시",
          field: "date",
          formatter: (cell) => {
            const v = cell.getValue();
            if (!v) return "";
            return `<span class="price-cell price-cell--date">${String(v).replace("T", " ").slice(0, 19)}</span>`;
          },
        },
        {
          title: "살 때 순금",
          field: "s_pure",
          hozAlign: "right",
          formatter: priceCellFormatter(statsByField.s_pure),
        },
        {
          title: "팔 때 순금",
          field: "p_pure",
          hozAlign: "right",
          formatter: priceCellFormatter(statsByField.p_pure),
        },
        {
          title: "팔 때 18K",
          field: "p_18k",
          hozAlign: "right",
          formatter: priceCellFormatter(statsByField.p_18k),
        },
        {
          title: "팔 때 14K",
          field: "p_14k",
          hozAlign: "right",
          formatter: priceCellFormatter(statsByField.p_14k),
        },
      ],
    });
  }

  async function load() {
    const days = document.getElementById("days").value;
    const metaEl = document.getElementById("meta");
    metaEl.textContent = "불러오는 중…";

    const url = `/api/prices?days=${encodeURIComponent(days)}&table_limit=200`;
    const res = await fetch(url);
    if (!res.ok) {
      metaEl.textContent = "불러오기 실패: " + res.status;
      return;
    }
    const json = await res.json();
    metaEl.textContent = fmtMeta(json.meta);

    buildChart(json.daily || []);
    buildTable(json.table || []);
  }

  document.getElementById("reload").addEventListener("click", load);
  document.getElementById("days").addEventListener("change", load);

  wireLegendToggles();
  load();
})();
