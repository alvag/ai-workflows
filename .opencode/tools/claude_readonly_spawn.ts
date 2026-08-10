import { tool } from "@opencode-ai/plugin";
import { spawnReadonly } from "../lib/claude-runner.ts";

export default tool({
  description: "Launch a direct, nonblocking Claude CLI read-only worker and return a durable handle.",
  args: {
    role: tool.schema.enum(["explore", "counter-plan", "investigate", "design-review", "debate", "diff", "pr", "refute"]),
    prompt_path: tool.schema.string(),
    context_paths: tool.schema.array(tool.schema.string()).optional(),
    working_dir: tool.schema.string(),
    run_id: tool.schema.string(),
    complexity: tool.schema.enum(["normal", "complex"]).optional(),
    high_risk: tool.schema.boolean().optional(),
    deadline_seconds: tool.schema.number().int().optional(),
  },
  async execute(args, context) {
    context.metadata({ title: `Claude ${args.role}`, metadata: { run_id: args.run_id } });
    return JSON.stringify(await spawnReadonly(context, {
      role: args.role,
      promptPath: args.prompt_path,
      contextPaths: args.context_paths,
      workingDir: args.working_dir,
      runId: args.run_id,
      complexity: args.complexity,
      highRisk: args.high_risk,
      deadlineSeconds: args.deadline_seconds,
    }), null, 2);
  },
});
