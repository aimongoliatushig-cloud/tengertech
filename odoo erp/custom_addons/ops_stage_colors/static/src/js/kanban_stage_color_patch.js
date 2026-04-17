/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

function normalizeStageName(name) {
    return (name || "")
        .toString()
        .trim()
        .toLowerCase();
}

patch(KanbanRenderer.prototype, {
    getGroupClasses(group, isGroupProcessing) {
        const baseClasses = super.getGroupClasses(group, isGroupProcessing);
        const name = normalizeStageName(group?.displayName);
        const extraClasses = [];

        if (
            name === "hiihdej baina" ||
            name === "yovagdaj bui ajil" ||
            name === "yavagdaj bui ajil" ||
            name === "явагдаж буй ажил"
        ) {
            extraClasses.push("ops_stage_blue");
        } else if (
            name === "shlagah" ||
            name === "shalgagdaj bui ajil" ||
            name === "шалгагдаж буй ажил"
        ) {
            extraClasses.push("ops_stage_yellow");
        } else if (
            name === "duussan" ||
            name === "duussan ajil" ||
            name === "дууссан ажил"
        ) {
            extraClasses.push("ops_stage_green");
        }

        return [baseClasses, ...extraClasses].filter(Boolean).join(" ");
    },
});
