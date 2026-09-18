import { reactive } from "vue";
import * as api from "./api";

const POLL_INTERVAL = 2500;
const MAX_WAIT = 3 * 60 * 1000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

type TaskOutcome =
  "success" | "failed" | "timeout" | "gone" | "error" | "cancelled";

type Payload = Record<string, any> | null;

export const waitForTask = async (
  taskId: string,
  isCancelled = () => false,
): Promise<TaskOutcome> => {
  const deadline = Date.now() + MAX_WAIT;
  while (!isCancelled()) {
    let task: { status?: string; exit_code?: number | null } | undefined;
    try {
      task = await api.getTask(taskId);
    } catch {
      return "error";
    }
    const status = task?.status;
    if (!status) return "gone";
    if (!["success", "failed", "killed"].includes(status)) {
      if (Date.now() > deadline) return "timeout";
      await sleep(POLL_INTERVAL);
      continue;
    }
    const succeeded =
      status === "success" &&
      (task?.exit_code === 0 || task?.exit_code == null);
    return succeeded ? "success" : "failed";
  }
  return "cancelled";
};

export const createStore = (context?: CloudContext) => {
  const state = reactive({
    context: context || {},
    billing: null as Payload,
    billingError: "",
    marketplace: null as Payload,
    marketplaceError: "",
    domains: null as Payload,
    domainsError: "",
  });

  const loadBilling = async (force = false) => {
    state.billingError = "";
    if (state.billing && !force) return;
    try {
      state.billing = await api.getBilling();
    } catch (exception) {
      state.billingError = api.getErrorMessage(exception);
    }
  };

  const loadMarketplace = async (force = false) => {
    state.marketplaceError = "";
    if (state.marketplace && !force) return;
    try {
      state.marketplace = await api.getMarketplaceApps();
    } catch (exception) {
      state.marketplaceError = api.getErrorMessage(exception);
    }
  };

  const loadDomains = async (force = false) => {
    state.domainsError = "";
    if (state.domains && !force) return;
    try {
      state.domains = await api.getDomains();
    } catch (exception) {
      state.domainsError = api.getErrorMessage(exception);
    }
  };

  return {
    state,
    api,
    loadBilling,
    loadMarketplace,
    loadDomains,
  };
};
