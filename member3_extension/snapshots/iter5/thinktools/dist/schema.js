import * as v from 'valibot';
const TOOL_DESCRIPTION = `A focused tool for sequential thinking and lightweight MCP tool coordination.
This tool supports reflective step-by-step problem solving, including revisions, branching, and tool-aware planning, while emphasizing only the essential context needed to keep the thought chain organized.

IMPORTANT: This server now concentrates on sequential thinking with streamlined tool coordination.
The LLM can still analyze available tools and recommend next actions, but advanced execution-tracking context is reduced to keep the interface simpler and easier to evolve.

When to use this tool:
- Breaking down complex problems into steps
- Planning and design with room for revision
- Analysis that might need course correction
- Problems where the full scope might not be clear initially
- Multi-step reasoning that should stay compact and focused
- Situations where tool suggestions should be tracked at a high level

Key features:
- Adjust total_thoughts as progress becomes clearer
- Revise or branch thoughts when needed
- Add more thoughts even after an initial endpoint
- Express uncertainty and explore alternatives
- Recommend tools for a step with concise rationale
- Track only the most relevant prior context for the next step

Parameters explained:
- available_mcp_tools: Array of MCP tool names available for use
- thought: Your current thinking step
- next_thought_needed: True if another thought step is needed
- thought_number: Current number in sequence
- total_thoughts: Current estimate of thoughts needed
- is_revision: Whether this thought revises previous thinking
- revises_thought: Which thought number is being reconsidered when revising
- branch_from_thought: Which thought number is the branching point when branching
- branch_id: Identifier for the current branch
- needs_more_thoughts: If more thoughts are needed after reaching an endpoint
- current_step: Current step recommendation
- previous_steps: Steps already recommended
- remaining_steps: High-level descriptions of upcoming steps

You should:
1. Start with an initial estimate of needed thoughts, but be ready to adjust
2. Revise or branch when needed
3. Continue thinking if more analysis is required
4. Express uncertainty when present
5. Ignore irrelevant information
6. Recommend tools with concise rationale
7. Track only the essential context needed for the next step
8. Provide a single, ideally correct answer as the final output
9. Only set next_thought_needed to false when truly done and a satisfactory answer is reached`;
export const ToolRecommendationSchema = v.object({
    tool_name: v.pipe(v.string(), v.description('Name of the tool being recommended')),
    confidence: v.pipe(v.number(), v.minValue(0), v.maxValue(1), v.description('0-1 indicating confidence in recommendation')),
    rationale: v.pipe(v.string(), v.description('Why this tool is recommended')),
    priority: v.pipe(v.number(), v.description('Order in the recommendation sequence')),
    suggested_inputs: v.optional(v.pipe(v.record(v.string(), v.unknown()), v.description('Optional suggested parameters'))),
    alternatives: v.optional(v.pipe(v.array(v.string()), v.description('Alternative tools that could be used')))
});
export const StepRecommendationSchema = v.object({
    step_description: v.pipe(v.string(), v.description('What needs to be done')),
    recommended_tools: v.pipe(v.array(ToolRecommendationSchema), v.description('Tools recommended for this step')),
    expected_outcome: v.pipe(v.string(), v.description('What to expect from this step')),
    next_step_conditions: v.optional(v.pipe(v.array(v.string()), v.description('Conditions to consider for the next step')))
});
const ToolExecutionFeedbackSchema = v.object({
    tool_name: v.pipe(v.string(), v.description('Name of the executed tool')),
    success: v.pipe(v.boolean(), v.description('Whether the tool execution succeeded')),
    execution_time_ms: v.optional(v.pipe(v.number(), v.description('Time taken to execute in milliseconds'))),
    output_summary: v.optional(v.pipe(v.string(), v.description('Brief summary of the tool output'))),
    error_message: v.optional(v.pipe(v.string(), v.description('Error message if execution failed')))
});

export const SequentialThinkingSchema = v.object({
    available_mcp_tools: v.pipe(v.array(v.string()), v.description('Array of MCP tool names available for use (e.g., ["mcp-omnisearch", "mcp-turso-cloud"])')),
    thought: v.pipe(v.string(), v.description('Your current thinking step')),
    next_thought_needed: v.pipe(v.boolean(), v.description('Whether another thought step is needed')),
    thought_number: v.pipe(v.number(), v.minValue(1), v.description('Current thought number')),
    total_thoughts: v.pipe(v.number(), v.minValue(1), v.description('Estimated total thoughts needed')),
    is_revision: v.optional(v.pipe(v.boolean(), v.description('Whether this revises previous thinking'))),
    revises_thought: v.optional(v.pipe(v.number(), v.minValue(1), v.description('Which thought is being reconsidered'))),
    branch_from_thought: v.optional(v.pipe(v.number(), v.minValue(1), v.description('Branching point thought number'))),
    branch_id: v.optional(v.pipe(v.string(), v.description('Branch identifier'))),
    needs_more_thoughts: v.optional(v.pipe(v.boolean(), v.description('If more thoughts are needed'))),
    current_step: v.optional(v.pipe(StepRecommendationSchema, v.description('Current step recommendation'))),
    previous_steps: v.optional(v.pipe(v.array(StepRecommendationSchema), v.description('Steps already recommended'))),
    remaining_steps: v.optional(v.pipe(v.array(v.string()), v.description('High-level descriptions of upcoming steps'))),
    max_branches: v.optional(v.pipe(v.number(), v.minValue(1), v.description('Maximum number of concurrent branches allowed (default: unlimited)'))),
    confidence_threshold: v.optional(v.pipe(v.number(), v.minValue(0), v.maxValue(1), v.description('Minimum confidence level (0-1) for tool recommendations (default: 0.0)'))),
    recommendation_strategy: v.optional(v.pipe(v.union([v.literal('conservative'), v.literal('balanced'), v.literal('exploratory')]), v.description('Strategy for tool recommendation: conservative (high confidence), balanced (default), or exploratory (include alternatives)')))
});
export const SEQUENTIAL_THINKING_TOOL = {
    name: 'sequentialthinking_tools',
    description: TOOL_DESCRIPTION,
    inputSchema: {} // This will be handled by tmcp with the schema above
};