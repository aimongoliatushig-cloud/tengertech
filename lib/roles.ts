export type UserRole =
  | "system_admin"
  | "general_manager"
  | "project_manager"
  | "team_leader"
  | "worker"
  | string;

export type RoleGroupFlags = {
  mfoManager: boolean;
  mfoDispatcher: boolean;
  mfoInspector: boolean;
  mfoMobile: boolean;
};

export type RoleContext = {
  role: UserRole;
  groupFlags?: Partial<RoleGroupFlags> | null;
};

export type AppRole =
  | "admin"
  | "executive"
  | "manager"
  | "dispatcher"
  | "inspector"
  | "leader"
  | "field_user";

export type Capability =
  | "create_projects"
  | "create_tasks"
  | "write_workspace_reports"
  | "view_quality_center"
  | "use_field_console";

const EMPTY_GROUP_FLAGS: RoleGroupFlags = {
  mfoManager: false,
  mfoDispatcher: false,
  mfoInspector: false,
  mfoMobile: false,
};

function normalizeGroupFlags(groupFlags?: Partial<RoleGroupFlags> | null): RoleGroupFlags {
  return {
    ...EMPTY_GROUP_FLAGS,
    ...(groupFlags || {}),
  };
}

export function getPrimaryAppRole(context: RoleContext): AppRole {
  const groupFlags = normalizeGroupFlags(context.groupFlags);

  if (context.role === "system_admin") {
    return "admin";
  }
  if (context.role === "general_manager") {
    return "executive";
  }
  if (groupFlags.mfoDispatcher) {
    return "dispatcher";
  }
  if (groupFlags.mfoInspector) {
    return "inspector";
  }
  if (context.role === "project_manager" || groupFlags.mfoManager) {
    return "manager";
  }
  if (context.role === "team_leader") {
    return "leader";
  }
  return "field_user";
}

export function getRoleLabel(role: UserRole) {
  switch (role) {
    case "system_admin":
      return "Системийн админ";
    case "general_manager":
      return "Ерөнхий менежер";
    case "project_manager":
      return "Ажлын менежер";
    case "team_leader":
      return "Багийн ахлагч";
    case "worker":
      return "Ажилтан";
    default:
      return "Хэрэглэгч";
  }
}

export function hasCapability(context: RoleContext, capability: Capability) {
  const groupFlags = normalizeGroupFlags(context.groupFlags);

  switch (capability) {
    case "create_projects":
      return context.role === "system_admin" || context.role === "general_manager";
    case "create_tasks":
      return (
        context.role === "system_admin" ||
        context.role === "general_manager" ||
        context.role === "project_manager"
      );
    case "write_workspace_reports":
      return context.role === "system_admin" || context.role === "team_leader";
    case "view_quality_center":
      return (
        context.role === "system_admin" ||
        context.role === "general_manager" ||
        context.role === "project_manager" ||
        groupFlags.mfoManager ||
        groupFlags.mfoDispatcher ||
        groupFlags.mfoInspector
      );
    case "use_field_console":
      return (
        context.role === "system_admin" ||
        context.role === "team_leader" ||
        context.role === "worker" ||
        groupFlags.mfoManager ||
        groupFlags.mfoDispatcher ||
        groupFlags.mfoInspector ||
        groupFlags.mfoMobile
      );
    default:
      return false;
  }
}
