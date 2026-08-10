import { tool } from "@opencode-ai/plugin";
import { spawnImplementation } from "../lib/claude-runner.ts";

export default tool({
  description: "Launch a direct, nonblocking Claude CLI writer from an approved frozen work order.",
  args: {
    work_order_path: tool.schema.string(),
    context_paths: tool.schema.array(tool.schema.string()).optional(),
    working_dir: tool.schema.string(),
    run_id: tool.schema.string(),
    proof_cmd: tool.schema.string().optional(),
    complexity: tool.schema.enum(["normal", "complex"]).optional(),
    high_risk: tool.schema.boolean().optional(),
    deadline_seconds: tool.schema.number().int().optional(),
  },
  async execute(args, context) {
    context.metadata({ title: "Claude implement", metadata: { run_id: args.run_id } });
    return JSON.stringify(await spawnImplementation(context, {
      workOrderPath: args.work_order_path,
      contextPaths: args.context_paths,
      workingDir: args.working_dir,
      runId: args.run_id,
      proofCommand: args.proof_cmd,
      complexity: args.complexity,
      highRisk: args.high_risk,
      deadlineSeconds: args.deadline_seconds,
    }), null, 2);
  },
});
