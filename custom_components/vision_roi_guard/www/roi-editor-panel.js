class VisionRoiGuardPanel extends HTMLElement {
  connectedCallback() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.entries = [];
      this.selectedEntryId = null;
      this.points = [];
      this.selectedIndex = null;
      this.dragIndex = null;
      this.dirty = false;
      this.imageVersion = Date.now();
      this.render();
    }
    this.loadEntries();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) this.connectedCallback();
    this.updateImageFromState();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100vh;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
        }
        .page {
          box-sizing: border-box;
          max-width: 1180px;
          margin: 0 auto;
          padding: 24px;
        }
        header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }
        h1 {
          flex: 1;
          margin: 0;
          font-size: 24px;
          font-weight: 500;
          letter-spacing: 0;
        }
        select, button {
          font: inherit;
          border-radius: 6px;
          border: 1px solid var(--divider-color);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          min-height: 36px;
        }
        select {
          min-width: 220px;
          padding: 0 34px 0 10px;
        }
        button {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 0 12px;
          cursor: pointer;
          white-space: nowrap;
        }
        button.primary {
          background: var(--primary-color);
          border-color: var(--primary-color);
          color: var(--text-primary-color);
        }
        button:disabled {
          cursor: default;
          opacity: 0.45;
        }
        .toolbar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
        }
        .status {
          color: var(--secondary-text-color);
          font-size: 13px;
          min-height: 20px;
          margin-left: auto;
        }
        .stage {
          position: relative;
          width: 100%;
          min-height: 320px;
          background: #151a1f;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          overflow: hidden;
          touch-action: none;
        }
        img {
          display: block;
          width: 100%;
          height: auto;
          user-select: none;
        }
        svg {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
        }
        polygon {
          fill: rgba(0, 172, 193, 0.22);
          stroke: #00acc1;
          stroke-width: 3;
        }
        line {
          stroke: #00acc1;
          stroke-width: 3;
        }
        circle {
          fill: #ffc107;
          stroke: #263238;
          stroke-width: 2;
          cursor: grab;
        }
        circle.selected {
          fill: #ff7043;
        }
        text {
          fill: #fff;
          font-size: 14px;
          font-weight: 700;
          pointer-events: none;
        }
        .empty {
          display: grid;
          min-height: 320px;
          place-items: center;
          color: var(--secondary-text-color);
          border: 1px solid var(--divider-color);
          border-radius: 8px;
        }
        @media (max-width: 720px) {
          .page { padding: 16px; }
          header { align-items: stretch; flex-direction: column; }
          select, button { width: 100%; }
          .toolbar { align-items: stretch; flex-direction: column; }
          .status { margin-left: 0; }
        }
      </style>
      <div class="page">
        <header>
          <h1>Vision ROI Guard</h1>
          <select class="entry"></select>
        </header>
        <div class="toolbar">
          <button class="refresh">Refresh frame</button>
          <button class="reload">Reload saved ROI</button>
          <button class="delete">Delete vertex</button>
          <button class="test">Run test analysis</button>
          <button class="save primary">Save ROI</button>
          <div class="status"></div>
        </div>
        <div class="stage">
          <img draggable="false" />
          <svg></svg>
        </div>
        <div class="empty" hidden>No Vision ROI Guard entries are configured.</div>
      </div>
    `;
    this.entrySelect = this.shadowRoot.querySelector(".entry");
    this.stage = this.shadowRoot.querySelector(".stage");
    this.img = this.shadowRoot.querySelector("img");
    this.svg = this.shadowRoot.querySelector("svg");
    this.status = this.shadowRoot.querySelector(".status");
    this.empty = this.shadowRoot.querySelector(".empty");
    this.refreshButton = this.shadowRoot.querySelector(".refresh");
    this.reloadButton = this.shadowRoot.querySelector(".reload");
    this.deleteButton = this.shadowRoot.querySelector(".delete");
    this.testButton = this.shadowRoot.querySelector(".test");
    this.saveButton = this.shadowRoot.querySelector(".save");

    this.entrySelect.addEventListener("change", () => this.selectEntry(this.entrySelect.value));
    this.refreshButton.addEventListener("click", () => this.refreshFrame());
    this.reloadButton.addEventListener("click", () => this.reloadSavedRoi());
    this.deleteButton.addEventListener("click", () => this.deleteSelected());
    this.testButton.addEventListener("click", () => this.runTestAnalysis());
    this.saveButton.addEventListener("click", () => this.save());
    this.stage.addEventListener("pointerdown", (event) => this.onPointerDown(event));
    this.stage.addEventListener("pointermove", (event) => this.onPointerMove(event));
    this.stage.addEventListener("pointerup", (event) => this.onPointerUp(event));
    this.stage.addEventListener("pointercancel", (event) => this.onPointerUp(event));
  }

  async loadEntries() {
    if (!this._hass) return;
    try {
      const result = await this._hass.callWS({ type: "vision_roi_guard/list_entries" });
      this.entries = result.entries || [];
      this.renderEntryOptions();
      if (!this.selectedEntryId && this.entries.length === 1) {
        this.selectEntry(this.entries[0].config_entry_id);
      } else if (!this.entries.some((entry) => entry.config_entry_id === this.selectedEntryId)) {
        this.selectEntry(this.entries[0]?.config_entry_id || null);
      } else {
        this.applySelectedEntry(false);
      }
    } catch (err) {
      this.setStatus(err?.message || "Could not load entries");
    }
  }

  renderEntryOptions() {
    this.entrySelect.innerHTML = "";
    for (const entry of this.entries) {
      const option = document.createElement("option");
      option.value = entry.config_entry_id;
      option.textContent = entry.title;
      this.entrySelect.appendChild(option);
    }
    this.empty.hidden = this.entries.length > 0;
    this.stage.hidden = this.entries.length === 0;
  }

  selectEntry(entryId) {
    this.selectedEntryId = entryId;
    this.entrySelect.value = entryId || "";
    this.applySelectedEntry(true);
  }

  applySelectedEntry(resetPoints) {
    const entry = this.selectedEntry;
    if (!entry) {
      this.points = [];
      this.draw();
      return;
    }
    if (resetPoints || !this.dirty) {
      this.points = (entry.roi_points || []).map((point) => [Number(point[0]), Number(point[1])]);
      this.selectedIndex = null;
      this.dirty = false;
    }
    this.sourceWidth = Number(entry.source_width || 0);
    this.sourceHeight = Number(entry.source_height || 0);
    this.updateImageFromState();
    this.draw();
  }

  get selectedEntry() {
    return this.entries.find((entry) => entry.config_entry_id === this.selectedEntryId) || null;
  }

  updateImageFromState() {
    if (!this._hass || !this.img) return;
    const entityId = this.selectedEntry?.entities?.roi_editor_image;
    if (!entityId) {
      this.img.removeAttribute("src");
      return;
    }
    const picture = this._hass.states[entityId]?.attributes?.entity_picture;
    this.img.src = picture
      ? this._hass.hassUrl(`${picture}${picture.includes("?") ? "&" : "?"}v=${this.imageVersion}`)
      : this._hass.hassUrl(`/api/image_proxy/${entityId}?v=${this.imageVersion}`);
  }

  draw() {
    const hasFrame = this.sourceWidth > 0 && this.sourceHeight > 0;
    this.svg.innerHTML = "";
    this.svg.setAttribute("viewBox", `0 0 ${this.sourceWidth || 1} ${this.sourceHeight || 1}`);
    this.refreshButton.disabled = !this.selectedEntry;
    this.reloadButton.disabled = !this.selectedEntry;
    this.testButton.disabled = !this.selectedEntry;
    this.deleteButton.disabled = this.selectedIndex === null || this.points.length <= 3;
    this.saveButton.disabled = !this.selectedEntry || this.points.length < 3;
    if (!this.selectedEntry) return;
    if (!hasFrame) {
      this.setStatus("Refresh frame to start editing.");
      return;
    }
    this.setStatus(`${this.points.length} vertices${this.dirty ? " - unsaved" : ""}`);
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
      circle.dataset.index = String(index);
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
    if (this.dragIndex !== null) this.stage.releasePointerCapture(event.pointerId);
    this.dragIndex = null;
  }

  deleteSelected() {
    if (this.selectedIndex === null || this.points.length <= 3) return;
    this.points.splice(this.selectedIndex, 1);
    this.selectedIndex = null;
    this.dirty = true;
    this.draw();
  }

  async refreshFrame() {
    const entry = this.selectedEntry;
    if (!entry) return;
    await this.withAction("Refreshing...", async () => {
      await this._hass.callService("vision_roi_guard", "refresh_roi_editor_image", {
        config_entry_id: entry.config_entry_id,
      });
      this.imageVersion = Date.now();
      await this.loadEntries();
    });
  }

  async runTestAnalysis() {
    const entry = this.selectedEntry;
    if (!entry) return;
    await this.withAction("Running analysis...", async () => {
      await this._hass.callService("vision_roi_guard", "run_analysis", {
        config_entry_id: entry.config_entry_id,
        force: true,
        save_debug: false,
      });
      this.imageVersion = Date.now();
      await this.loadEntries();
    });
  }

  reloadSavedRoi() {
    this.applySelectedEntry(true);
  }

  async save() {
    const entry = this.selectedEntry;
    if (!entry) return;
    await this.withAction("Saving...", async () => {
      await this._hass.callService("vision_roi_guard", "update_roi", {
        config_entry_id: entry.config_entry_id,
        points: this.points,
      });
      this.dirty = false;
      this.imageVersion = Date.now();
      await this.loadEntries();
    });
  }

  async withAction(label, action) {
    this.setBusy(true);
    this.setStatus(label);
    let message = "Done";
    try {
      await action();
    } catch (err) {
      message = err?.message || "Action failed";
    } finally {
      this.setBusy(false);
      this.draw();
      this.setStatus(message);
    }
  }

  setBusy(isBusy) {
    for (const button of [
      this.refreshButton,
      this.reloadButton,
      this.deleteButton,
      this.testButton,
      this.saveButton,
    ]) {
      button.disabled = isBusy;
    }
    this.entrySelect.disabled = isBusy;
  }

  setStatus(message) {
    this.status.textContent = message || "";
  }
}

customElements.define("vision-roi-guard-panel", VisionRoiGuardPanel);
