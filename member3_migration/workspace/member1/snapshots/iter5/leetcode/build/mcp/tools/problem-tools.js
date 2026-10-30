import { z } from "zod";
import { PROBLEM_CATEGORIES, PROBLEM_TAGS } from "../../common/constants.js";
import { ToolRegistry } from "./tool-registry.js";
/**
 * Problem tool registry class that handles registration of LeetCode problem-related tools.
 * This class manages tools for accessing problem details, searching problems, and daily challenges.
 */
export class ProblemToolRegistry extends ToolRegistry {
    registerCommon() {
        // Problem details tool
        // Problem hints tool
        this.server.tool("get_problem_hints", "Retrieves progressive hints for a specific LeetCode problem to assist with solving without revealing the complete solution. Provides graduated guidance for learning purposes", {
            titleSlug: z
                .string()
                .describe("The URL slug/identifier of the problem (e.g., 'two-sum', 'add-two-numbers') to retrieve hints for")
        }, async ({ titleSlug }) => {
            const problemData = await this.leetcodeService.fetchProblemSimplified(titleSlug);
            const hints = problemData.hints || [];
            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify({
                            titleSlug,
                            problemTitle: problemData.title,
                            hintsAvailable: hints.length,
                            hints: hints
                        })
                    }
                ]
            };
        });
        this.server.tool("get_problem", "Retrieves complete details about a specific LeetCode problem, including its full description, examples, constraints, test cases, and all related information. Use this for comprehensive problem analysis. Also supports fetching today's LeetCode Daily Challenge by setting the 'daily' parameter to true (titleSlug is not required in that case)", {
            titleSlug: z
                .string()
                .optional()
                .describe("The URL slug/identifier of the problem (e.g., 'two-sum', 'add-two-numbers') as it appears in the LeetCode URL. Not required when 'daily' is true"),
            daily: z
                .boolean()
                .optional()
                .default(false)
                .describe("When set to true, retrieves today's LeetCode Daily Challenge problem instead of a specific problem by slug")
        }, async ({ titleSlug, daily }) => {
            if (daily) {
                const data = await this.leetcodeService.fetchDailyChallenge();
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                date: new Date().toISOString().split("T")[0],
                                problem: data
                            })
                        }
                    ]
                };
            }
            if (!titleSlug) {
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({ error: "titleSlug is required when 'daily' is not set to true" })
                        }
                    ]
                };
            }
            const data = await this.leetcodeService.fetchProblemSimplified(titleSlug);
            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify({
                            titleSlug,
                            problem: data
                        })
                    }
                ]
            };
        });
        // Search problems tool
        this.server.tool("search_problems", "Searches for LeetCode problems based on multiple filter criteria including categories, tags, difficulty levels, and keywords, with pagination support", {
            category: z
                .enum(PROBLEM_CATEGORIES)
                .default("all-code-essentials")
                .describe("Problem category filter (e.g., 'algorithms', 'database', 'shell') to narrow down the problem domain"),
            tags: z
                .array(z.enum(PROBLEM_TAGS))
                .optional()
                .describe("List of topic tags to filter problems by (e.g., ['array', 'dynamic-programming', 'tree'])"),
            difficulty: z
                .enum(["EASY", "MEDIUM", "HARD"])
                .optional()
                .describe("Problem difficulty level filter to show only problems of a specific difficulty"),
            searchKeywords: z
                .string()
                .optional()
                .describe("Keywords to search in problem titles and descriptions"),
            status: z
                .enum(["SOLVED", "ATTEMPTED", "NOT_STARTED"])
                .optional()
                .describe("Filter problems by user's completion status - SOLVED (fully completed), ATTEMPTED (tried but not solved), or NOT_STARTED (never attempted)"),
            premiumOnly: z
                .boolean()
                .optional()
                .describe("When true, returns only premium problems; when false, returns only free problems; when undefined, returns all problems regardless of premium status"),
            orderBy: z
                .enum(["FRONTEND_ID", "DIFFICULTY", "ACCEPTANCE_RATE", "FREQUENCY"])
                .optional()
                .describe("Sort order for returned problems - by problem ID (default), difficulty level, acceptance rate, or frequency in interviews"),
            limit: z
                .number()
                .optional()
                .default(10)
                .describe("Maximum number of problems to return in a single request (for pagination)"),
            offset: z
                .number()
                .optional()
                .describe("Number of problems to skip (for pagination)")
        }, async ({ category, tags, difficulty, limit, offset, searchKeywords, status, premiumOnly, orderBy }) => {
            const data = await this.leetcodeService.searchProblems(category, tags, difficulty, limit, offset, searchKeywords, status, premiumOnly, orderBy);
            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify({
                            filters: { tags, difficulty, searchKeywords, status, premiumOnly, orderBy },
                            pagination: { limit, offset },
                            problems: data
                        })
                    }
                ]
            };
        });
    }
}
/**
 * Registers all problem-related tools with the MCP server.
 *
 * @param server - The MCP server instance to register tools with
 * @param leetcodeService - The LeetCode service implementation to use for API calls
 */
export function registerProblemTools(server, leetcodeService) {
    const registry = new ProblemToolRegistry(server, leetcodeService);
    registry.registerTools();
}
//# sourceMappingURL=problem-tools.js.map