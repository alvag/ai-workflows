import { tool } from "@opencode-ai/plugin";
import { resumeClaude } from "../lib/claude-runner.ts";

export default tool({
  description: "Resume a completed direct Claude CLI session with a delta file and return a new handle.",
  args: {
    handle: tool.schema.string(),
    delta_path: tool.schema.string(),
    deadline_seconds: tool.schema.number().int().optional(),
  },
  async execute(args, context) {
    context.metadata({ title: "Claude resume", metadata: { parent_handle: args.handle } });
    return JSON.stringify(await resumeClaude(context, {
      handle: args.handle,
      deltaPath: args.delta_path,
      deadlineSeconds: args.deadline_seconds,
    }), null, 2);
  },
});
