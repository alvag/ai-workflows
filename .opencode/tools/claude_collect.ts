import { tool } from "@opencode-ai/plugin";
import { collectClaude } from "../lib/claude-runner.ts";

export default tool({
  description: "Poll or collect a direct Claude CLI worker by durable handle; enforces official first-party provider evidence.",
  args: {
    handle: tool.schema.string(),
    wait: tool.schema.boolean().optional(),
    deadline_seconds: tool.schema.number().int().optional(),
  },
  async execute(args, context) {
    context.metadata({ title: "Claude collect", metadata: { handle: args.handle } });
    return JSON.stringify(await collectClaude(context, {
      handle: args.handle,
      wait: args.wait,
      deadlineSeconds: args.deadline_seconds,
    }), null, 2);
  },
});
