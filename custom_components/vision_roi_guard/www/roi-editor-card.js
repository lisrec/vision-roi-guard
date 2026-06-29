class VisionRoiEditorCard extends HTMLElement {
  setConfig(config) {
    if (!config.guard_entity || !config.image_entity) {
      throw new Error("guard_entity and image_entity are required");
    }
    this.config = config;
    this.points = [];
    this.dragIndex = null;
    this.selectedIndex = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.render();
    }
    this.syncFromState();
    this.update();
  }

  getCardSize() {
    return 6;
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }
        .wrap { padding: 16px; }
        .stage {
          position: relative;
          width: 100%;
          background: #111820;
          border-radius: 6px;
          overflow: hidden;
          touch-action: none;
        }
        img { display: block; width: 100%; height: auto; user-select: none; }
        svg { position: absolute; inset: 0; width: 100%; height: 100%; }
        polygon { fill: rgba(0, 172, 193, 0.22); stroke: #00acc1; stroke-width: 3; }
        line { stroke: #00acc1; stroke-width: 3; }
        circle { fill: #ffc107; stroke: #263238; stroke-width: 2; cursor: grab; }
        circle.selected { fill: #ff7043; }
        text { fill: #fff; font-size: 14px; font-weight: 700; pointer-events: none; }
        .bar { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
        .bar .spacer { flex: 1; }
        .status { color: var(--secondary-text-color); font-size: 13px; min-height: 18px; }
        button {
          border: 1px solid var(--divider-color);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          border-radius: 6px;
          padding: 7px 10px;
          cursor: pointer;
        }
        button.primary {
          background: var(--primary-color);
          border-color: var(--primary-color);
          color: var(--text-primary-color);
        }
        button:disabled { opacity: 0.45; cursor: default; }
      </style>
      <ha-card>
        <div class="wrap">
          <div class="stage">
            <img draggable="false" />
            <svg></svg>
          </div>
          <div class="bar">
            <div class="status"></div>
            <div class="spacer"></div>
            <button class="delete" title="Delete selected vertex">Delete</button>
            <button class="save primary" title="Save ROI">Save</button>
          </div>
        </div>
      </ha-card>
    `;
    this.stage = this.shadowRoot.querySelector(".stage");
    this.img = this.shadowRoot.querySelector("img");
    this.svg = this.shadowRoot.querySelector("svg");
    this.status = this.shadowRoot.querySelector(".status");
    this.deleteButton = this.shadowRoot.querySelector(".delete");
    this.saveButton = this.shadowRoot.querySelector(".save");
    this.stage.addEventListener("pointerdown", (event) => this.onPointerDown(event));
    this.stage.addEventListener("pointermove", (event) => this.onPointerMove(event));
    this.stage.addEventListener("pointerup", (event) => this.onPointerUp(event));
    this.stage.addEventListener("pointercancel", (event) => this.onPointerUp(event));
    this.deleteButton.addEventListener("click", () => this.deleteSelected());
    this.saveButton.addEventListener("click", () => this.save());
  }

  syncFromState() {
    if (this.dirty || !this._hass || !this.config) return;
    const state = this._hass.states[this.config.guard_entity];
    const attrPoints = state?.attributes?.roi_points;
    if (Array.isArray(attrPoints)) {
      this.points = attrPoints.map((point) => [Number(point[0]), Number(point[1])]);
    }
  }

  update() {
    if (!this._hass || !this.config) return;
    const imageState = this._hass.states[this.config.image_entity];
    const guardState = this._hass.states[this.config.guard_entity];
    const width = Number(guardState?.attributes?.source_width || 0);
    const height = Number(guardState?.attributes?.source_height || 0);
    this.sourceWidth = width;
    this.sourceHeight = height;
    this.svg.setAttribute("viewBox", `0 0 ${width || 1} ${height || 1}`);
    const picture = imageState?.attributes?.entity_picture;
    this.img.src = picture
      ? this._hass.hassUrl(picture)
      : this._hass.hassUrl(`/api/image_proxy/${this.config.image_entity}?t=${Date.now()}`);
    this.draw();
  }

  draw() {
    const hasFrame = this.sourceWidth > 0 && this.sourceHeight > 0;
    this.svg.innerHTML = "";
    this.deleteButton.disabled = this.selectedIndex === null || this.points.length <= 3;
    this.saveButton.disabled = this.points.length < 3;
    if (!hasFrame) {
      this.status.textContent = "Run analysis once to create a full-frame editor image.";
      return;
    }
    this.status.textContent = `${this.points.length} vertices`;
    if (this.points.length >= 3) {
      const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      polygon.setAttribute("points", this.points.map((point) => point.join(",")).join(" "));
      this.svg.appendChild(polygon);
    } else if (this.points.length === 2) {
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", this.points[0][0]);
      line.setAttribute("y1", this.points[0][1]);
      line.setAttribute("x2", this.points[1][0]);
      line.setAttribute("y2", this.points[1][1]);
      this.svg.appendChild(line);
    }
    this.points.forEach((point, index) => {
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", point[0]);
      circle.setAttribute("cy", point[1]);
      circle.setAttribute("r", 10);
      circle.dataset.index = index;
      if (index === this.selectedIndex) circle.classList.add("selected");
      this.svg.appendChild(circle);

      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", point[0] + 13);
      label.setAttribute("y", point[1] - 10);
      label.textContent = String(index + 1);
      this.svg.appendChild(label);
    });
  }

  toImagePoint(event) {
    const rect = this.stage.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * this.sourceWidth;
    const y = ((event.clientY - rect.top) / rect.height) * this.sourceHeight;
    return [
      Math.max(0, Math.min(this.sourceWidth - 1, Math.round(x))),
      Math.max(0, Math.min(this.sourceHeight - 1, Math.round(y))),
    ];
  }

  onPointerDown(event) {
    if (!this.sourceWidth || !this.sourceHeight) return;
    const targetIndex = event.target?.dataset?.index;
    if (targetIndex !== undefined) {
      this.dragIndex = Number(targetIndex);
      this.selectedIndex = this.dragIndex;
      this.stage.setPointerCapture(event.pointerId);
      this.draw();
      return;
    }
    this.points.push(this.toImagePoint(event));
    this.selectedIndex = this.points.length - 1;
    this.dirty = true;
    this.draw();
  }

  onPointerMove(event) {
    if (this.dragIndex === null) return;
    this.points[this.dragIndex] = this.toImagePoint(event);
    this.dirty = true;
    this.draw();
  }

  onPointerUp(event) {
    if (this.dragIndex !== null) {
      this.stage.releasePointerCapture(event.pointerId);
    }
    this.dragIndex = null;
  }

  deleteSelected() {
    if (this.selectedIndex === null || this.points.length <= 3) return;
    this.points.splice(this.selectedIndex, 1);
    this.selectedIndex = null;
    this.dirty = true;
    this.draw();
  }

  async save() {
    this.status.textContent = "Saving...";
    try {
      await this._hass.callService("vision_roi_guard", "update_roi", {
        entity_id: this.config.guard_entity,
        points: this.points,
      });
      this.dirty = false;
      this.status.textContent = "Saved";
    } catch (err) {
      this.status.textContent = err?.message || "Save failed";
    }
  }
}

customElements.define("vision-roi-editor-card", VisionRoiEditorCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vision-roi-editor-card",
  name: "Vision ROI Editor",
  description: "Draw and save a Vision ROI Guard polygon.",
});
