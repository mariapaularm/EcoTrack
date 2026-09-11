const FACTORS = {
  transport: 0.21, // kg CO2 / km
  electricity: 0.5, // kg CO2 / kWh
  meat: 2.5, // kg CO2 / día con carne
};

const WEEKLY_TARGET = 50;

const form = document.getElementById("carbon-form");
const results = document.getElementById("resultados");
const tipsSection = document.getElementById("recomendaciones");
const tipsList = document.getElementById("tips-list");

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const km = Number(document.getElementById("km").value);
  const kwh = Number(document.getElementById("kwh").value);
  const meatDays = Number(document.getElementById("meat-days").value);

  if (![km, kwh, meatDays].every(Number.isFinite) || km < 0 || kwh < 0 || meatDays < 0 || meatDays > 7) {
    alert("Revisa los datos: usa números válidos (días de carne entre 0 y 7).");
    return;
  }

  const transport = km * FACTORS.transport;
  const electricity = kwh * FACTORS.electricity;
  const food = meatDays * FACTORS.meat;
  const total = transport + electricity + food;

  renderResults({ transport, electricity, food, total });
  renderTips({ km, kwh, meatDays, transport, electricity, food, total });
});

function renderResults({ transport, electricity, food, total }) {
  results.hidden = false;
  tipsSection.hidden = false;

  document.getElementById("total-co2").textContent = total.toFixed(1);
  document.getElementById("transport-co2").textContent = `${transport.toFixed(1)} kg`;
  document.getElementById("electric-co2").textContent = `${electricity.toFixed(1)} kg`;
  document.getElementById("food-co2").textContent = `${food.toFixed(1)} kg`;
  document.getElementById("impact-level").textContent = impactLabel(total);

  const maxPart = Math.max(transport, electricity, food, 1);
  setBar("bar-transport", (transport / maxPart) * 100);
  setBar("bar-electric", (electricity / maxPart) * 100);
  setBar("bar-food", (food / maxPart) * 100);

  const progress = Math.min((total / WEEKLY_TARGET) * 100, 100);
  document.getElementById("progress-fill").style.width = `${progress}%`;
  document.getElementById("progress-caption").textContent = `${total.toFixed(1)} / ${WEEKLY_TARGET} kg`;
  document.getElementById("progress-bar").setAttribute("aria-valuenow", total.toFixed(1));
}

function setBar(id, percent) {
  document.getElementById(id).style.width = `${percent}%`;
}

function impactLabel(total) {
  if (total < 25) return "Impacto bajo — buen ritmo";
  if (total < 50) return "Impacto moderado — hay margen";
  return "Impacto alto — prioriza cambios";
}

function renderTips(data) {
  const tips = [];
  const { km, kwh, meatDays, transport, electricity, food, total } = data;
  const top = [
    { name: "transporte", value: transport },
    { name: "electricidad", value: electricity },
    { name: "alimentación", value: food },
  ].sort((a, b) => b.value - a.value)[0];

  tips.push(
    `Tu mayor fuente esta semana es ${top.name} (${top.value.toFixed(1)} kg CO₂). Empieza por ahí.`
  );

  if (km > 50) {
    tips.push("Agrupa trayectos, usa transporte público o comparte coche para recortar kilómetros.");
  } else {
    tips.push("Mantén trayectos cortos: caminar o usar bici en distancias urbanas reduce aún más el total.");
  }

  if (kwh > 30) {
    tips.push("Baja 2–3 °C la calefacción/aire y apaga standby: cada kWh ahorrado evita 0.5 kg de CO₂.");
  } else {
    tips.push("Buen consumo eléctrico. Revisa bombillas LED y electrodomésticos en modo eco para sostenerlo.");
  }

  if (meatDays >= 5) {
    tips.push("Prueba 2 días sin carne esta semana: cada día menos evita unos 2.5 kg de CO₂.");
  } else if (meatDays === 0) {
    tips.push("Alimentación de bajo impacto. Compleméntala con productos locales y de temporada.");
  } else {
    tips.push("Sustituye una comida con carne por legumbres o pescado local para bajar la huella alimentaria.");
  }

  if (total > WEEKLY_TARGET) {
    tips.push(`Estás ${ (total - WEEKLY_TARGET).toFixed(1) } kg por encima de la meta de 50 kg. Elige un hábito y mídilo de nuevo.`);
  } else {
    tips.push("Vas dentro de la meta semanal. Conserva el hábito y registra otra semana para comparar.");
  }

  tipsList.innerHTML = tips.map((tip) => `<li>${tip}</li>`).join("");
}
