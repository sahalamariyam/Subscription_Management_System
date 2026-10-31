/** @odoo-module **/
/**
 * Brightloop Finance — OWL Financial Dashboard Component
 *
 * Renders KPI cards, collection rate bar, recent payments table,
 * and XLSX export trigger. Fetches all data from the server-side
 * `brightloop.finance.dashboard` TransientModel via JSON-RPC.
 *
 * Member 4 — brightloop_finance
 * Odoo 18 Community (OWL 2 component system)
 */

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/** Return today's date as YYYY-MM-DD */
function todayStr() {
    return new Date().toISOString().split("T")[0];
}

/** Return the first day of the current month as YYYY-MM-DD */
function firstOfMonthStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

class FinanceDashboard extends Component {
    static template = "brightloop_finance.FinanceDashboard";
    static props = {};

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            error: null,
            dateFrom: firstOfMonthStr(),
            dateTo: todayStr(),
            kpis: {
                active_subscription_count: 0,
                paused_subscription_count: 0,
                revenue_received: 0,
                total_invoice_value: 0,
                total_outstanding: 0,
                overdue_invoice_count: 0,
                overdue_amount: 0,
            },
            payments: [],
        });

        onWillStart(async () => {
            await this.loadKPIs();
        });
    }

    /** ------------------------------------------------------------------ **/
    /** Data loading                                                         */
    /** ------------------------------------------------------------------ **/

    async loadKPIs() {
        this.state.loading = true;
        this.state.error = null;
        try {
            // Create a transient dashboard record and read KPIs
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "brightloop.finance.dashboard",
                method: "get_dashboard_kpis",
                args: [this.state.dateFrom, this.state.dateTo],
                kwargs: {},
            });

            if (result && result.kpis) {
                this.state.kpis = result.kpis;
            }
            if (result && result.payments) {
                this.state.payments = result.payments;
            }
        } catch (e) {
            const msg = e && e.message ? e.message : "Failed to load dashboard data.";
            this.state.error = msg;
            console.error("[BrightloopFinanceDashboard] loadKPIs error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    /** ------------------------------------------------------------------ **/
    /** Helpers                                                              */
    /** ------------------------------------------------------------------ **/

    formatCurrency(value) {
        if (value === undefined || value === null) return "$0.00";
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 2,
        }).format(Number(value));
    }

    collectionRate() {
        const invoiced = Number(this.state.kpis.total_invoice_value) || 0;
        const received = Number(this.state.kpis.revenue_received) || 0;
        if (invoiced === 0) return 0;
        return Math.min(100, Math.round((received / invoiced) * 100));
    }

    /** ------------------------------------------------------------------ **/
    /** Event handlers                                                       */
    /** ------------------------------------------------------------------ **/

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
    }

    resetDates() {
        this.state.dateFrom = firstOfMonthStr();
        this.state.dateTo = todayStr();
        this.loadKPIs();
    }

    async exportXLSX() {
        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "brightloop.finance.export",
                method: "export_xlsx",
                args: [],
                kwargs: {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                },
            });

            if (result && result.file_content) {
                // Trigger browser download
                const byteChars = atob(result.file_content);
                const byteNums = Array.from(byteChars, (c) => c.charCodeAt(0));
                const blob = new Blob([new Uint8Array(byteNums)], {
                    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = result.filename || "brightloop_finance_report.xlsx";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                this.notification.add("XLSX report downloaded successfully.", {
                    type: "success",
                    sticky: false,
                });
            }
        } catch (e) {
            this.notification.add("Export failed: " + (e.message || "unknown error"), {
                type: "danger",
                sticky: true,
            });
            console.error("[BrightloopFinanceDashboard] exportXLSX error:", e);
        }
    }
}

// Register as a client action so it can be opened via action_finance_dashboard_owl
registry.category("actions").add("brightloop_finance_dashboard", FinanceDashboard);
