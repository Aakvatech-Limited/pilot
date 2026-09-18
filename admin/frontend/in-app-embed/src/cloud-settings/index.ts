import { defineCustomElement, h } from "vue";
import styleText from "./tailwind.css?inline";
import CloudSettings from "./CloudSettings.vue";

const TAG = "fc-cloud-settings";

const scopeTokens = (text: string) =>
  text
    .replace(/:root\b/g, ":host")
    .replace(/\[data-theme=(["']?)dark\1\]/g, ":host([data-theme=dark])");

const sheet = new CSSStyleSheet();
sheet.replaceSync(scopeTokens(styleText));

if (import.meta.hot) {
  import.meta.hot.accept("./tailwind.css?inline", (module) => {
    if (module) sheet.replaceSync(scopeTokens(module.default));
  });
}

const CloudSettingsElement = defineCustomElement({
  props: { context: Object, open: Boolean },
  emits: ["close"],
  shadowRoot: true,
  configureApp(app) {
    app.config.globalProperties.__ = window.__;
  },
  setup(props, { emit }) {
    return () =>
      h(CloudSettings, {
        context: props.context,
        open: props.open,
        onClose: () => emit("close"),
      });
  },
});

class CloudSettingsHost extends CloudSettingsElement {
  themeObserver?: MutationObserver;

  connectedCallback() {
    super.connectedCallback();
    const root = this.shadowRoot!;
    if (!root.adoptedStyleSheets.includes(sheet)) {
      root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
    }
    this.syncTheme();
    this.themeObserver = new MutationObserver(() => this.syncTheme());
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback?.();
    this.themeObserver?.disconnect();
  }

  syncTheme() {
    const theme =
      document.documentElement.getAttribute("data-theme") || "light";
    this.setAttribute("data-theme", theme);
  }
}

if (!customElements.get(TAG)) customElements.define(TAG, CloudSettingsHost);

frappe.cloudSettings = {
  show(context) {
    let host = document.querySelector<CloudSettingsHost>(TAG);
    if (!host) {
      host = document.createElement(TAG) as CloudSettingsHost;
      host.addEventListener("close", () => {
        host!.open = false;
      });
      document.body.appendChild(host);
    }
    host.context = context || {};
    host.open = true;
  },
};
