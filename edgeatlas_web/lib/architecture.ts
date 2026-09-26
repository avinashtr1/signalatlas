import { readFile } from "fs/promises";
import path from "path";

const REGISTRY_ROOT =
  process.env.SIGNALATLAS_REGISTRY_ROOT ||
  "/root/.openclaw/workspace/signalatlas_registry";

export type ArchitectureDocument = {
  key: string;
  title: string;
  filename: string;
  content: string;
  available: boolean;
};

export type RegistrySummary = {
  filename: string;
  available: boolean;
  facts: Array<[string, string]>;
};

const DOCUMENTS = [
  ["system_map", "Current System Map", "SYSTEM_MAP.md"],
  ["architecture", "Canonical Architecture", "CANONICAL_ARCHITECTURE.md"],
  ["roadmap", "Master Roadmap", "SIGNALATLAS_MASTER_ROADMAP.md"],
  ["api_doc", "API Registry", "SIGNALATLAS_API_REGISTRY.md"],
  ["engine_doc", "Engine Registry", "SIGNALATLAS_ENGINE_REGISTRY.md"],
] as const;

const REGISTRIES = [
  "ENGINE_REGISTRY.json",
  "API_REGISTRY.json",
  "ANALYTICS_REGISTRY.json",
  "DASHBOARD_REGISTRY.json",
  "TELEGRAM_REGISTRY.json",
] as const;

export async function loadArchitectureDocuments(): Promise<
  ArchitectureDocument[]
> {
  return Promise.all(
    DOCUMENTS.map(async ([key, title, filename]) => {
      try {
        const content = await readFile(
          path.join(REGISTRY_ROOT, filename),
          "utf8"
        );

        return {
          key,
          title,
          filename,
          content,
          available: true,
        };
      } catch {
        return {
          key,
          title,
          filename,
          content: "",
          available: false,
        };
      }
    })
  );
}

export async function loadRegistrySummaries(): Promise<
  RegistrySummary[]
> {
  return Promise.all(
    REGISTRIES.map(async (filename) => {
      try {
        const raw = await readFile(
          path.join(REGISTRY_ROOT, filename),
          "utf8"
        );

        const parsed: unknown = JSON.parse(raw);

        return {
          filename,
          available: true,
          facts: collectInterestingFacts(parsed).slice(0, 14),
        };
      } catch {
        return {
          filename,
          available: false,
          facts: [],
        };
      }
    })
  );
}

function collectInterestingFacts(
  value: unknown,
  prefix = "",
  depth = 0
): Array<[string, string]> {
  if (
    depth > 5 ||
    !value ||
    typeof value !== "object" ||
    Array.isArray(value)
  ) {
    return [];
  }

  const allowed = new Set([
    "status",
    "mode",
    "host",
    "bind",
    "port",
    "path",
    "canonical",
    "read_only",
    "enabled",
    "active",
    "coverage",
    "complete_universe",
    "database",
    "backing_store",
    "backing_database",
    "service",
    "routes",
  ]);

  const out: Array<[string, string]> = [];

  for (const [key, child] of Object.entries(
    value as Record<string, unknown>
  )) {
    const name = prefix ? `${prefix}.${key}` : key;

    if (allowed.has(key)) {
      const formatted = formatFact(child);

      if (formatted !== null) {
        out.push([name, formatted]);
      }
    }

    if (
      child &&
      typeof child === "object" &&
      !Array.isArray(child)
    ) {
      out.push(
        ...collectInterestingFacts(
          child,
          name,
          depth + 1
        )
      );
    }
  }

  return dedupeFacts(out);
}

function formatFact(value: unknown): string | null {
  if (value === null || value === undefined) return null;

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  if (Array.isArray(value)) {
    return `${value.length} items`;
  }

  return null;
}

function dedupeFacts(
  rows: Array<[string, string]>
): Array<[string, string]> {
  const seen = new Set<string>();
  const out: Array<[string, string]> = [];

  for (const row of rows) {
    const key = `${row[0]}=${row[1]}`;

    if (seen.has(key)) continue;

    seen.add(key);
    out.push(row);
  }

  return out;
}
