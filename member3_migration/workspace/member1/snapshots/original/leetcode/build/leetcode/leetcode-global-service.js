import logger from "../utils/logger.js";
import { SEARCH_PROBLEMS_QUERY } from "./graphql/global/search-problems.js";
import { SOLUTION_ARTICLE_DETAIL_QUERY } from "./graphql/global/solution-article-detail.js";
import { SOLUTION_ARTICLES_QUERY } from "./graphql/global/solution-articles.js";
/**
 * LeetCode Global API Service Implementation
 *
 * This class provides methods to interact with the LeetCode Global API
 */
export class LeetCodeGlobalService {
    leetCodeApi;
    credential;
    constructor(leetCodeApi, credential) {
        this.leetCodeApi = leetCodeApi;
        this.credential = credential;
    }
    async fetchUserSubmissionDetail(id) {
        if (!this.isAuthenticated()) {
            throw new Error("Authentication required to fetch user submission detail");
        }
        return await this.leetCodeApi.submission(id);
    }
    async fetchUserStatus() {
        if (!this.isAuthenticated()) {
            throw new Error("Authentication required to fetch user status");
        }
        return await this.leetCodeApi.whoami().then((res) => {
            return {
                isSignedIn: res?.isSignedIn ?? false,
                username: res?.username ?? "",
                avatar: res?.avatar ?? "",
                isAdmin: res?.isAdmin ?? false
            };
        });
    }
    async fetchUserAllSubmissions(options) {
        if (!this.isAuthenticated()) {
            throw new Error("Authentication required to fetch user submissions");
        }
        const submissions = await this.leetCodeApi.submissions({
            offset: options.offset ?? 0,
            limit: options.limit ?? 20,
            slug: options.questionSlug
        });
        return { submissions };
    }
    /**
     * 获取用户最近的提交记录
     * @param username
     * @param limit
     * @returns
     */
    async fetchUserRecentSubmissions(username, limit) {
        return await this.leetCodeApi.recent_submissions(username, limit);
    }
    /**
     * 获取用户最近 AC 的提交记录
     * @param username
     * @param limit
     * @returns
     */
    async fetchUserRecentACSubmissions(username, limit) {
        return await this.leetCodeApi.graphql({
            query: `
                    query ($username: String!, $limit: Int) {
                        recentAcSubmissionList(username: $username, limit: $limit) {
                            id
                            title
                            titleSlug
                            time
                            timestamp
                            statusDisplay
                            lang
                        }
                    }

                `,
            variables: {
                username,
                limit
            }
        });
    }
    async fetchUserProfile(username) {
        const profile = await this.leetCodeApi.user(username);
        if (profile && profile.matchedUser) {
            const { matchedUser } = profile;
            return {
                username: matchedUser.username,
                realName: matchedUser.profile.realName,
                userAvatar: matchedUser.profile.userAvatar,
                countryName: matchedUser.profile.countryName,
                githubUrl: matchedUser.githubUrl,
                company: matchedUser.profile.company,
                school: matchedUser.profile.school,
                ranking: matchedUser.profile.ranking,
                totalSubmissionNum: matchedUser.submitStats?.totalSubmissionNum
            };
        }
        return profile;
    }
    async fetchUserContestRanking(username, attended = true) {
        const contestInfo = await this.leetCodeApi.user_contest_info(username);
        if (contestInfo.userContestRankingHistory && attended) {
            contestInfo.userContestRankingHistory =
                contestInfo.userContestRankingHistory.filter((contest) => {
                    return contest && contest.attended;
                });
        }
        return contestInfo;
    }
    async fetchDailyChallenge() {
        const dailyChallenge = await this.leetCodeApi.daily();
        return dailyChallenge;
    }
    async fetchProblem(titleSlug) {
        const problem = await this.leetCodeApi.problem(titleSlug);
        return problem;
    }
    async fetchProblemSimplified(titleSlug) {
        const problem = await this.fetchProblem(titleSlug);
        if (!problem) {
            throw new Error(`Problem ${titleSlug} not found`);
        }
        const filteredTopicTags = problem.topicTags?.map((tag) => tag.slug) || [];
        const filteredCodeSnippets = problem.codeSnippets?.filter((snippet) => ["cpp", "python3", "java"].includes(snippet.langSlug)) || [];
        let parsedSimilarQuestions = [];
        if (problem.similarQuestions) {
            try {
                const allQuestions = JSON.parse(problem.similarQuestions);
                parsedSimilarQuestions = allQuestions
                    .slice(0, 3)
                    .map((q) => ({
                    titleSlug: q.titleSlug,
                    difficulty: q.difficulty
                }));
            }
            catch (e) {
                logger.error("Error parsing similarQuestions: %s", e);
            }
        }
        return {
            titleSlug,
            questionId: problem.questionId,
            title: problem.title,
            content: problem.content,
            difficulty: problem.difficulty,
            topicTags: filteredTopicTags,
            codeSnippets: filteredCodeSnippets,
            exampleTestcases: problem.exampleTestcases,
            hints: problem.hints,
            similarQuestions: parsedSimilarQuestions
        };
    }
    async searchProblems(category, tags, difficulty, limit = 10, offset = 0, searchKeywords) {
        const filters = {};
        if (difficulty) {
            filters.difficulty = difficulty.toUpperCase();
        }
        if (tags && tags.length > 0) {
            filters.tags = tags;
        }
        if (searchKeywords) {
            filters.searchKeywords = searchKeywords;
        }
        const response = await this.leetCodeApi.graphql({
            query: SEARCH_PROBLEMS_QUERY,
            variables: {
                categorySlug: category,
                limit,
                skip: offset,
                filters
            }
        });
        const questionList = response.data?.problemsetQuestionList;
        if (!questionList) {
            return {
                total: 0,
                questions: []
            };
        }
        return {
            total: questionList.total,
            questions: questionList.questions.map((question) => ({
                title: question.title,
                titleSlug: question.titleSlug,
                difficulty: question.difficulty,
                acRate: question.acRate,
                topicTags: question.topicTags.map((tag) => tag.slug)
            }))
        };
    }
    async fetchUserProgressQuestionList(options) {
        if (!this.isAuthenticated()) {
            throw new Error("Authentication required to fetch user progress question list");
        }
        const filters = {
            skip: options?.offset || 0,
            limit: options?.limit || 20,
            questionStatus: options?.questionStatus,
            difficulty: options?.difficulty
        };
        return await this.leetCodeApi.user_progress_questions(filters);
    }
    /**
     * Retrieves a list of solutions for a specific problem.
     *
     * @param questionSlug - The URL slug/identifier of the problem
     * @param options - Optional parameters for filtering and sorting the solutions
     * @returns Promise resolving to the solutions list data
     */
    async fetchQuestionSolutionArticles(questionSlug, options) {
        const variables = {
            questionSlug,
            first: options?.limit || 5,
            skip: options?.skip || 0,
            orderBy: options?.orderBy || "HOT",
            userInput: options?.userInput,
            tagSlugs: options?.tagSlugs ?? []
        };
        return await this.leetCodeApi
            .graphql({
            query: SOLUTION_ARTICLES_QUERY,
            variables
        })
            .then((res) => {
            const ugcArticleSolutionArticles = res.data?.ugcArticleSolutionArticles;
            if (!ugcArticleSolutionArticles) {
                return {
                    totalNum: 0,
                    hasNextPage: false,
                    articles: []
                };
            }
            const data = {
                totalNum: ugcArticleSolutionArticles?.totalNum || 0,
                hasNextPage: ugcArticleSolutionArticles?.pageInfo?.hasNextPage ||
                    false,
                articles: ugcArticleSolutionArticles?.edges
                    ?.map((edge) => {
                    if (edge?.node &&
                        edge.node.topicId &&
                        edge.node.slug) {
                        edge.node.articleUrl = `https://leetcode.com/problems/${questionSlug}/solutions/${edge.node.topicId}/${edge.node.slug}`;
                    }
                    return edge.node;
                })
                    .filter((node) => node && node.canSee) || []
            };
            return data;
        });
    }
    /**
     * Retrieves detailed information about a specific solution on LeetCode Global.
     *
     * @param topicId - The topic ID of the solution
     * @returns Promise resolving to the solution detail data
     */
    async fetchSolutionArticleDetail(topicId) {
        return await this.leetCodeApi
            .graphql({
            query: SOLUTION_ARTICLE_DETAIL_QUERY,
            variables: {
                topicId
            }
        })
            .then((response) => {
            return response.data?.ugcArticleSolutionArticle;
        });
    }
    /**
     * Note feature is not supported in LeetCode Global.
     * This method is implemented to satisfy the interface but will always throw an error.
     *
     * @param options - Query parameters (not used)
     * @throws Error indicating the feature is not supported on Global platform
     */
    async fetchUserNotes(options) {
        throw new Error("Notes feature is not supported in LeetCode Global");
    }
    /**
     * Note feature is not supported in LeetCode Global.
     * This method is implemented to satisfy the interface but will always throw an error.
     *
     * @param questionId - The question ID (not used)
     * @param limit - Maximum number of notes (not used)
     * @param skip - Pagination offset (not used)
     * @throws Error indicating the feature is not supported on Global platform
     */
    async fetchNotesByQuestionId(questionId, limit, skip) {
        throw new Error("Notes feature is not supported in LeetCode Global");
    }
    /**
     * Note feature is not supported in LeetCode Global.
     * This method is implemented to satisfy the interface but will always throw an error.
     */
    async createUserNote(content, noteType, targetId, summary) {
        throw new Error("Notes feature is not supported in LeetCode Global");
    }
    /**
     * Note feature is not supported in LeetCode Global.
     * This method is implemented to satisfy the interface but will always throw an error.
     */
    async updateUserNote(noteId, content, summary) {
        throw new Error("Notes feature is not supported in LeetCode Global");
    }
    isAuthenticated() {
        return (!!this.credential &&
            !!this.credential.csrf &&
            !!this.credential.session);
    }
    isCN() {
        return false;
    }
}
//# sourceMappingURL=leetcode-global-service.js.map