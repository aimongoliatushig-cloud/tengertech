/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProjectTaskStateSelection } from "@project/components/project_task_state_selection/project_task_state_selection";

const WORKFLOW_LABELS = new Map([
    ["04_waiting_normal", "Хийгдэх"],
    ["01_in_progress", "Явагдаж буй"],
    ["02_changes_requested", "Шалгагдаж буй"],
    ["03_approved", "Зөвшөөрсөн"],
    ["1_done", "Дууссан"],
    ["1_canceled", "Цуцлагдсан"],
]);

const WORKFLOW_ORDER = [
    "04_waiting_normal",
    "01_in_progress",
    "02_changes_requested",
    "03_approved",
    "1_done",
    "1_canceled",
];

patch(ProjectTaskStateSelection.prototype, {
    get options() {
        const baseSelection = this.props.record.fields[this.props.name].selection || [];
        const labelsByState = new Map(baseSelection);
        return WORKFLOW_ORDER.filter((state) => labelsByState.has(state)).map((state) => [
            state,
            WORKFLOW_LABELS.get(state) || labelsByState.get(state),
        ]);
    },

    get availableOptions() {
        return this.options;
    },

    get label() {
        return WORKFLOW_LABELS.get(this.currentValue) || this.currentValue;
    },
});
