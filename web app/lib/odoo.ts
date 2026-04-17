import "server-only";

type OdooRelation = [number, string] | false;

type OdooProjectRecord = {
  id: number;
  name: string;
  user_id: OdooRelation;
  ops_department_id: OdooRelation;
  date_start: string | false;
  date: string | false;
};

type OdooTaskRecord = {
  id: number;
  name: string;
  project_id: OdooRelation;
  stage_id: OdooRelation;
  ops_team_leader_id: OdooRelation;
  user_ids: number[];
  ops_planned_quantity: number;
  ops_completed_quantity: number;
  ops_remaining_quantity: number;
  ops_progress_percent: number;
  ops_measurement_unit: string | false;
  priority: string;
  date_deadline: string | false;
  state: string;
};

type OdooReportRecord = {
  id: number;
  task_id: OdooRelation;
  reporter_id: OdooRelation;
  report_datetime: string;
  report_summary: string | false;
  reported_quantity: number;
  image_count: number;
  audio_count: number;
};

type OdooUserRecord = {
  id: number;
  name: string;
  login: string;
  ops_user_type: string | false;
};

type DepartmentCard = {
  name: string;
  label: string;
  accent: string;
  openTasks: number;
  reviewTasks: number;
  completion: number;
};

type ProjectCard = {
  id: number;
  name: string;
  manager: string;
  departmentName: string;
  stageLabel: string;
  stageBucket: StageBucket;
  openTasks: number;
  completion: number;
  deadline: string;
  href: string;
};

type ReviewItem = {
  id: number;
  name: string;
  stageLabel: string;
  deadline: string;
  projectName: string;
  leaderName: string;
  progress: number;
  href: string;
};

type LiveTask = {
  id: number;
  name: string;
  projectName: string;
  stageLabel: string;
  stageBucket: StageBucket;
  deadline: string;
  plannedQuantity: number;
  completedQuantity: number;
  remainingQuantity: number;
  measurementUnit: string;
  leaderName: string;
  priorityLabel: string;
  progress: number;
  href: string;
};

type ReportFeedItem = {
  id: number;
  reporter: string;
  taskName: string;
  projectName: string;
  summary: string;
  reportedQuantity: number;
  imageCount: number;
  audioCount: number;
  submittedAt: string;
};

type TeamLeaderCard = {
  name: string;
  activeTasks: number;
  reviewTasks: number;
  averageCompletion: number;
  squadSize: number;
};

type DashboardMetric = {
  label: string;
  value: string;
  note: string;
  tone: "amber" | "teal" | "red" | "slate";
};

export type OdooConnection = {
  url: string;
  db: string;
  login: string;
  password: string;
};

export type AuthenticatedOdooUser = {
  uid: number;
  user: {
    name: string;
    login: string;
    role: string;
  };
};

export type DashboardSnapshot = {
  source: "live" | "demo";
  generatedAt: string;
  metrics: DashboardMetric[];
  departments: DepartmentCard[];
  projects: ProjectCard[];
  liveTasks: LiveTask[];
  reviewQueue: ReviewItem[];
  reports: ReportFeedItem[];
  teamLeaders: TeamLeaderCard[];
  odooBaseUrl: string;
  totalTasks: number;
};

type StageBucket = "todo" | "progress" | "review" | "done" | "unknown";

const DEFAULT_CONNECTION: OdooConnection = {
  url: process.env.ODOO_URL ?? "http://localhost:8069",
  db: process.env.ODOO_DB ?? "odoo19_admin",
  login: process.env.ODOO_LOGIN ?? "admin",
  password: process.env.ODOO_PASSWORD ?? "admin",
};

export function createOdooConnection(
  overrides: Partial<OdooConnection> = {},
): OdooConnection {
  return {
    ...DEFAULT_CONNECTION,
    ...overrides,
  };
}

const DEPARTMENT_ORDER = [
  "Авто бааз",
  "Хог тээвэрлэлт",
  "Ногоон байгууламж",
  "Зам талбайн цэвэрлэгээ",
  "Тохижилт үйлчилгээ",
] as const;

const DEPARTMENT_LABELS: Record<(typeof DEPARTMENT_ORDER)[number], string> = {
  "Авто бааз": "Техник, тээврийн бэлэн байдал",
  "Хог тээвэрлэлт": "Ачилт, маршрут, цуглуулалт",
  "Ногоон байгууламж": "Мод, зүлэг, хэлбэржүүлэлт",
  "Зам талбайн цэвэрлэгээ": "Зам, талбай, явган зам",
  "Тохижилт үйлчилгээ": "Нийтийн талбай, засвар, жижиг ажил",
};

const DEPARTMENT_ACCENTS: Record<(typeof DEPARTMENT_ORDER)[number], string> = {
  "Авто бааз": "var(--tone-amber)",
  "Хог тээвэрлэлт": "var(--tone-red)",
  "Ногоон байгууламж": "var(--tone-teal)",
  "Зам талбайн цэвэрлэгээ": "var(--tone-blue)",
  "Тохижилт үйлчилгээ": "var(--tone-slate)",
};

const STAGE_LABELS: Record<StageBucket, string> = {
  todo: "Хийгдэх ажил",
  progress: "Явагдаж буй ажил",
  review: "Шалгагдаж буй ажил",
  done: "Дууссан ажил",
  unknown: "Тодорхойгүй",
};

const KNOWN_STAGE_MATCHERS: Array<[StageBucket, string[]]> = [
  ["todo", ["хийгдэх", "todo", "task"]],
  ["progress", ["явагдаж", "progress", "hiihdej", "in progress"]],
  ["review", ["шалгагдаж", "review", "changes requested", "shalgagdaj", "shalgah"]],
  ["done", ["дууссан", "done", "completed", "duussan"]],
];

function getStageBucket(stageName?: string | null): StageBucket {
  const normalized = (stageName ?? "").trim().toLowerCase();
  for (const [bucket, matchers] of KNOWN_STAGE_MATCHERS) {
    if (matchers.some((item) => normalized.includes(item))) {
      return bucket;
    }
  }
  return "unknown";
}

function relationName(relation: OdooRelation, fallback = "Оноогоогүй") {
  return Array.isArray(relation) ? relation[1] : fallback;
}

function formatCompactDate(value?: string | false) {
  if (!value) {
    return "Товлоогүй";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("mn-MN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function formatSyncDate(value: Date) {
  return new Intl.DateTimeFormat("mn-MN", {
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function formatQuantity(value: number, unit: string) {
  return `${Math.round(value * 10) / 10} ${unit}`.trim();
}

function priorityLabel(priority: string) {
  switch (priority) {
    case "3":
      return "Яаралтай";
    case "2":
      return "Өндөр";
    case "1":
      return "Дунд";
    default:
      return "Тогтмол";
  }
}

function mapTaskToDepartment(task: Pick<OdooTaskRecord, "name" | "project_id">) {
  const haystack = `${task.name} ${relationName(task.project_id, "")}`.toLowerCase();
  if (haystack.includes("мод") || haystack.includes("ногоон")) {
    return "Ногоон байгууламж";
  }
  if (haystack.includes("хог")) {
    return "Хог тээвэрлэлт";
  }
  if (haystack.includes("авто") || haystack.includes("машин") || haystack.includes("техник")) {
    return "Авто бааз";
  }
  if (haystack.includes("зам") || haystack.includes("талбай") || haystack.includes("цэвэрлэгээ")) {
    return "Зам талбайн цэвэрлэгээ";
  }
  return "Тохижилт үйлчилгээ";
}

function resolveProjectDepartmentName(
  project: Pick<OdooProjectRecord, "ops_department_id">,
  fallback = "Тодорхойгүй",
) {
  return relationName(project.ops_department_id, fallback);
}

function resolveDepartmentLabel(name: string) {
  return DEPARTMENT_LABELS[name as keyof typeof DEPARTMENT_LABELS] ?? "Төслийн харьяалал";
}

function resolveDepartmentAccent(name: string) {
  return DEPARTMENT_ACCENTS[name as keyof typeof DEPARTMENT_ACCENTS] ?? "var(--tone-slate)";
}

async function jsonRpc<T>(
  service: "common" | "object",
  method: string,
  args: unknown[],
  connection: OdooConnection,
) {
  const response = await fetch(`${connection.url}/jsonrpc`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "call",
      params: {
        service,
        method,
        args,
      },
      id: `${service}-${method}-${Date.now()}`,
    }),
  });

  if (!response.ok) {
    throw new Error(`Odoo JSON-RPC failed with HTTP ${response.status}`);
  }

  const payload = (await response.json()) as { result?: T; error?: { message?: string } };
  if (payload.error) {
    throw new Error(payload.error.message ?? "Unknown Odoo JSON-RPC error");
  }

  return payload.result as T;
}

async function authenticate(connection: OdooConnection) {
  return jsonRpc<number | false>(
    "common",
    "authenticate",
    [connection.db, connection.login, connection.password, {}],
    connection,
  );
}

export async function authenticateOdooUser(
  login: string,
  password: string,
): Promise<AuthenticatedOdooUser | null> {
  const connection = createOdooConnection({ login, password });
  const uid = await authenticate(connection);

  if (!uid) {
    return null;
  }

  const users = await executeKw<OdooUserRecord[]>(
    uid,
    "res.users",
    "search_read",
    [[["id", "=", uid]]],
    {
      fields: ["name", "login", "ops_user_type"],
      limit: 1,
    },
    connection,
  );

  const user = users[0];
  if (!user) {
    return null;
  }

  return {
    uid,
    user: {
      name: user.name,
      login: user.login,
      role: user.ops_user_type || "worker",
    },
  };
}

async function executeKw<T>(
  uid: number,
  model: string,
  method: string,
  methodArgs: unknown[],
  kwargs: Record<string, unknown>,
  connection: OdooConnection,
) {
  return jsonRpc<T>(
    "object",
    "execute_kw",
    [connection.db, uid, connection.password, model, method, methodArgs, kwargs],
    connection,
  );
}

export async function executeOdooKw<T>(
  model: string,
  method: string,
  methodArgs: unknown[],
  kwargs: Record<string, unknown> = {},
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const connection = createOdooConnection(connectionOverrides);
  const uid = await authenticate(connection);

  if (!uid) {
    throw new Error("Odoo authentication failed");
  }

  return executeKw<T>(uid, model, method, methodArgs, kwargs, connection);
}

async function fetchLiveSnapshot(connection: OdooConnection): Promise<DashboardSnapshot> {
  const uid = await authenticate(connection);
  if (!uid) {
    throw new Error("Odoo authentication failed");
  }

  const [projects, tasks, reports] = await Promise.all([
    executeKw<OdooProjectRecord[]>(
      uid,
      "project.project",
      "search_read",
      [[]],
      {
        fields: ["name", "user_id", "ops_department_id", "date_start", "date"],
        limit: 12,
        order: "create_date desc",
      },
      connection,
    ),
    executeKw<OdooTaskRecord[]>(
      uid,
      "project.task",
      "search_read",
      [[["project_id", "!=", false]]],
      {
        fields: [
          "name",
          "project_id",
          "stage_id",
          "ops_team_leader_id",
          "user_ids",
          "ops_planned_quantity",
          "ops_completed_quantity",
          "ops_remaining_quantity",
          "ops_progress_percent",
          "ops_measurement_unit",
          "priority",
          "date_deadline",
          "state",
        ],
        limit: 120,
        order: "priority desc, date_deadline asc, create_date desc",
      },
      connection,
    ),
    executeKw<OdooReportRecord[]>(
      uid,
      "ops.task.report",
      "search_read",
      [[]],
      {
        fields: [
          "task_id",
          "reporter_id",
          "report_datetime",
          "report_summary",
          "reported_quantity",
          "image_count",
          "audio_count",
        ],
        limit: 32,
        order: "report_datetime desc",
      },
      connection,
    ),
  ]);

  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((task) => getStageBucket(relationName(task.stage_id, "")) === "done");
  const reviewTasks = tasks.filter((task) => getStageBucket(relationName(task.stage_id, "")) === "review");
  const activeTasks = tasks.filter((task) => {
    const bucket = getStageBucket(relationName(task.stage_id, ""));
    return bucket === "todo" || bucket === "progress";
  });
  const overdueTasks = tasks.filter((task) => {
    if (!task.date_deadline) {
      return false;
    }
    const bucket = getStageBucket(relationName(task.stage_id, ""));
    if (bucket === "done") {
      return false;
    }
    return new Date(task.date_deadline).getTime() < Date.now();
  });

  const projectDepartmentById = new Map(
    projects.map((project) => [
      project.id,
      Array.isArray(project.ops_department_id)
        ? project.ops_department_id[1]
        : mapTaskToDepartment({ name: project.name, project_id: false }),
    ]),
  );

  const departmentNames = [
    ...DEPARTMENT_ORDER.filter((name) =>
      [...projectDepartmentById.values(), ...tasks.map((task) => mapTaskToDepartment(task))].includes(name),
    ),
    ...[...projectDepartmentById.values()]
      .filter((name) => name && !DEPARTMENT_ORDER.includes(name as (typeof DEPARTMENT_ORDER)[number]))
      .sort((left, right) => left.localeCompare(right, "mn")),
  ];

  const departments = departmentNames.map((department) => {
    const departmentTasks = tasks.filter((task) => {
      const projectId = Array.isArray(task.project_id) ? task.project_id[0] : null;
      const departmentName = projectId
        ? projectDepartmentById.get(projectId) || mapTaskToDepartment(task)
        : mapTaskToDepartment(task);
      return departmentName === department;
    });
    const departmentDone = departmentTasks.filter(
      (task) => getStageBucket(relationName(task.stage_id, "")) === "done",
    );
    const departmentReview = departmentTasks.filter(
      (task) => getStageBucket(relationName(task.stage_id, "")) === "review",
    );

    return {
      name: department,
      label: resolveDepartmentLabel(department),
      accent: resolveDepartmentAccent(department),
      openTasks: departmentTasks.length - departmentDone.length,
      reviewTasks: departmentReview.length,
      completion: departmentTasks.length
        ? Math.round((departmentDone.length / departmentTasks.length) * 100)
        : 0,
    };
  });

  const projectsWithStats = projects.map((project) => {
    const projectTasks = tasks.filter((task) => relationName(task.project_id, "") === project.name);
    const completed = projectTasks.filter(
      (task) => getStageBucket(relationName(task.stage_id, "")) === "done",
    ).length;
    const buckets = projectTasks.map((task) => getStageBucket(relationName(task.stage_id, "")));
    const stageBucket =
      buckets.includes("review")
        ? "review"
        : buckets.includes("progress")
          ? "progress"
          : buckets.includes("todo")
            ? "todo"
            : buckets.includes("done")
              ? "done"
              : "unknown";

    return {
      id: project.id,
      name: project.name,
      manager: relationName(project.user_id),
      departmentName: resolveProjectDepartmentName(project),
      stageLabel: STAGE_LABELS[stageBucket],
      stageBucket,
      openTasks: projectTasks.length - completed,
      completion: projectTasks.length ? Math.round((completed / projectTasks.length) * 100) : 0,
      deadline: formatCompactDate(project.date),
      href: `/projects/${project.id}`,
    } satisfies ProjectCard;
  });

  const liveTasks = activeTasks.slice(0, 8).map((task) => ({
    id: task.id,
    name: task.name,
    projectName: relationName(task.project_id),
    stageLabel: STAGE_LABELS[getStageBucket(relationName(task.stage_id, ""))],
    stageBucket: getStageBucket(relationName(task.stage_id, "")),
    deadline: formatCompactDate(task.date_deadline),
    plannedQuantity: task.ops_planned_quantity ?? 0,
    completedQuantity: task.ops_completed_quantity ?? 0,
    remainingQuantity: task.ops_remaining_quantity ?? 0,
    measurementUnit: task.ops_measurement_unit || "ш",
    leaderName: relationName(task.ops_team_leader_id),
    priorityLabel: priorityLabel(task.priority),
    progress: Math.round(task.ops_progress_percent ?? 0),
    href: `/tasks/${task.id}`,
  }));

  const reviewQueue = reviewTasks.slice(0, 6).map((task) => ({
    id: task.id,
    name: task.name,
    stageLabel: relationName(task.stage_id, STAGE_LABELS.review),
    deadline: formatCompactDate(task.date_deadline),
    projectName: relationName(task.project_id),
    leaderName: relationName(task.ops_team_leader_id),
    progress: Math.round(task.ops_progress_percent ?? 0),
    href: `/tasks/${task.id}`,
  }));

  const reportTaskMap = new Map(tasks.map((task) => [task.id, task]));
  const reportsFeed = reports.slice(0, 6).map((report) => {
    const task = Array.isArray(report.task_id) ? reportTaskMap.get(report.task_id[0]) : undefined;
    return {
      id: report.id,
      reporter: relationName(report.reporter_id),
      taskName: relationName(report.task_id),
      projectName: task ? relationName(task.project_id) : "Төсөлгүй",
      summary: report.report_summary || "Тайлбар оруулаагүй",
      reportedQuantity: report.reported_quantity ?? 0,
      imageCount: report.image_count ?? 0,
      audioCount: report.audio_count ?? 0,
      submittedAt: formatCompactDate(report.report_datetime),
    } satisfies ReportFeedItem;
  });

  const teamLeaderMap = new Map<string, TeamLeaderCard>();
  for (const task of tasks) {
    const leaderName = relationName(task.ops_team_leader_id, "Оноогоогүй");
    const entry = teamLeaderMap.get(leaderName) ?? {
      name: leaderName,
      activeTasks: 0,
      reviewTasks: 0,
      averageCompletion: 0,
      squadSize: Math.max((task.user_ids?.length ?? 1) - 1, 0),
    };

    const bucket = getStageBucket(relationName(task.stage_id, ""));
    if (bucket === "review") {
      entry.reviewTasks += 1;
    }
    if (bucket === "todo" || bucket === "progress") {
      entry.activeTasks += 1;
    }
    entry.averageCompletion += task.ops_progress_percent ?? 0;
    entry.squadSize = Math.max(entry.squadSize, Math.max((task.user_ids?.length ?? 1) - 1, 0));
    teamLeaderMap.set(leaderName, entry);
  }

  const teamLeaders = Array.from(teamLeaderMap.values())
    .map((leader) => {
      const relatedTasks = tasks.filter(
        (task) => relationName(task.ops_team_leader_id, "Оноогоогүй") === leader.name,
      );
      const totalProgress = relatedTasks.reduce(
        (sum, task) => sum + (task.ops_progress_percent ?? 0),
        0,
      );
      return {
        ...leader,
        averageCompletion: relatedTasks.length ? Math.round(totalProgress / relatedTasks.length) : 0,
      };
    })
    .sort((left, right) => right.activeTasks - left.activeTasks)
    .slice(0, 4);

  const completionRate = totalTasks ? Math.round((doneTasks.length / totalTasks) * 100) : 0;
  const completedQuantity = tasks.reduce(
    (sum, task) => sum + (task.ops_completed_quantity ?? 0),
    0,
  );

  return {
    source: "live",
    generatedAt: formatSyncDate(new Date()),
    odooBaseUrl: connection.url,
    totalTasks,
    metrics: [
      {
        label: "Идэвхтэй ажил",
        value: String(activeTasks.length),
        note: `${overdueTasks.length} нь хугацаа давсан`,
        tone: overdueTasks.length ? "red" : "slate",
      },
      {
        label: "Шалгалтын дараалал",
        value: String(reviewTasks.length),
        note: "Ерөнхий менежер баталгаажуулалт хүлээж байна",
        tone: "amber",
      },
      {
        label: "Нийт гүйцэтгэл",
        value: `${completionRate}%`,
        note: `${doneTasks.length}/${totalTasks} task дууссан`,
        tone: "teal",
      },
      {
        label: "Хэмжээний биелэлт",
        value: formatQuantity(completedQuantity, "нэгж"),
        note: "Field report-оос автоматаар тооцсон",
        tone: "slate",
      },
    ],
    departments,
    projects: projectsWithStats.slice(0, 6),
    liveTasks,
    reviewQueue,
    reports: reportsFeed,
    teamLeaders,
  };
}

function fallbackSnapshot(): DashboardSnapshot {
  return {
    source: "demo",
    generatedAt: formatSyncDate(new Date()),
    odooBaseUrl: DEFAULT_CONNECTION.url,
    totalTasks: 28,
    metrics: [
      {
        label: "Идэвхтэй ажил",
        value: "18",
        note: "3 нь хугацаа давсан",
        tone: "red",
      },
      {
        label: "Шалгалтын дараалал",
        value: "4",
        note: "Ерөнхий менежер review хийж байна",
        tone: "amber",
      },
      {
        label: "Нийт гүйцэтгэл",
        value: "64%",
        note: "18/28 task дээр ахиц бүртгэгдсэн",
        tone: "teal",
      },
      {
        label: "Хэмжээний биелэлт",
        value: "713 мод",
        note: "Өнөөдрийн тайлангаас автоматаар тооцсон",
        tone: "slate",
      },
    ],
    departments: DEPARTMENT_ORDER.map((name, index) => ({
      name,
      label: DEPARTMENT_LABELS[name],
      accent: DEPARTMENT_ACCENTS[name],
      openTasks: [4, 5, 9, 6, 4][index],
      reviewTasks: [1, 0, 2, 1, 0][index],
      completion: [58, 67, 72, 49, 63][index],
    })),
    projects: [
      {
        id: 1,
        name: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        manager: "BATAA",
        departmentName: "Ногоон байгууламж",
        stageLabel: "Шалгагдаж буй ажил",
        stageBucket: "review",
        openTasks: 14,
        completion: 71,
        deadline: "4-р сарын 20, 18:00",
        href: "/projects/1",
      },
      {
        id: 2,
        name: "Хог тээвэрлэлтийн өглөөний маршрут",
        manager: "ankhaa",
        departmentName: "Хог тээвэрлэлт",
        stageLabel: "Явагдаж буй ажил",
        stageBucket: "progress",
        openTasks: 5,
        completion: 62,
        deadline: "Өнөөдөр 20:00",
        href: "/projects/2",
      },
      {
        id: 3,
        name: "Зам талбайн шөнийн цэвэрлэгээ",
        manager: "ankhaa",
        departmentName: "Зам талбайн цэвэрлэгээ",
        stageLabel: "Хийгдэх ажил",
        stageBucket: "todo",
        openTasks: 6,
        completion: 35,
        deadline: "4-р сарын 17, 06:00",
        href: "/projects/3",
      },
    ],
    liveTasks: [
      {
        id: 101,
        name: "1-р хороо - 20-р байрны ар тал",
        projectName: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        stageLabel: "Явагдаж буй ажил",
        stageBucket: "progress",
        deadline: "Өнөөдөр 18:00",
        plannedQuantity: 48,
        completedQuantity: 21,
        remainingQuantity: 27,
        measurementUnit: "мод",
        leaderName: "suldee",
        priorityLabel: "Өндөр",
        progress: 44,
        href: "/tasks/101",
      },
      {
        id: 102,
        name: "7-р хороо - Төв замын захын цэвэрлэгээ",
        projectName: "Зам талбайн шөнийн цэвэрлэгээ",
        stageLabel: "Хийгдэх ажил",
        stageBucket: "todo",
        deadline: "Маргааш 06:00",
        plannedQuantity: 12,
        completedQuantity: 0,
        remainingQuantity: 12,
        measurementUnit: "км²",
        leaderName: "temuulen",
        priorityLabel: "Яаралтай",
        progress: 0,
        href: "/tasks/102",
      },
      {
        id: 103,
        name: "Авто бааз - 3 машинд урсгал үйлчилгээ",
        projectName: "Техникийн өдөр тутмын бэлэн байдал",
        stageLabel: "Явагдаж буй ажил",
        stageBucket: "progress",
        deadline: "Өнөөдөр 17:30",
        plannedQuantity: 3,
        completedQuantity: 1,
        remainingQuantity: 2,
        measurementUnit: "машин",
        leaderName: "bold",
        priorityLabel: "Дунд",
        progress: 33,
        href: "/tasks/103",
      },
    ],
    reviewQueue: [
      {
        id: 201,
        name: "5-р хороо - 32 модны тайлан",
        stageLabel: "Шалгагдаж буй ажил",
        deadline: "Өнөөдөр 16:30",
        projectName: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        leaderName: "suldee",
        progress: 100,
        href: "/tasks/201",
      },
      {
        id: 202,
        name: "Хог тээврийн 2-р маршрут",
        stageLabel: "Шалгагдаж буй ажил",
        deadline: "Өнөөдөр 19:00",
        projectName: "Хог тээвэрлэлтийн өглөөний маршрут",
        leaderName: "sarangerel",
        progress: 88,
        href: "/tasks/202",
      },
    ],
    reports: [
      {
        id: 301,
        reporter: "suldee",
        taskName: "1-р хороо - 20-р байрны ар тал",
        projectName: "2026 Мод хэлбэржүүлэлтийн хуваарь",
        summary: "21 мод хэлбэржүүлж, 1 зураг, 1 аудио тайлан хавсаргасан.",
        reportedQuantity: 21,
        imageCount: 1,
        audioCount: 1,
        submittedAt: "Өнөөдөр 15:30",
      },
      {
        id: 302,
        reporter: "sarangerel",
        taskName: "Хог тээврийн 2-р маршрут",
        projectName: "Хог тээвэрлэлтийн өглөөний маршрут",
        summary: "Маршрут дууссан, дахин ачилт 18:00-д эхэлнэ.",
        reportedQuantity: 4,
        imageCount: 2,
        audioCount: 0,
        submittedAt: "Өнөөдөр 14:10",
      },
    ],
    teamLeaders: [
      {
        name: "suldee",
        activeTasks: 3,
        reviewTasks: 1,
        averageCompletion: 68,
        squadSize: 5,
      },
      {
        name: "sarangerel",
        activeTasks: 4,
        reviewTasks: 1,
        averageCompletion: 73,
        squadSize: 6,
      },
      {
        name: "bold",
        activeTasks: 2,
        reviewTasks: 0,
        averageCompletion: 51,
        squadSize: 4,
      },
    ],
  };
}

export async function loadMunicipalSnapshot(
  connectionOverrides: Partial<OdooConnection> = {},
) {
  const connection = createOdooConnection(connectionOverrides);

  try {
    return await fetchLiveSnapshot(connection);
  } catch (error) {
    console.warn("Falling back to demo dashboard snapshot:", error);
    return fallbackSnapshot();
  }
}
