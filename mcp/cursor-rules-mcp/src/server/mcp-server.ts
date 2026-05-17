import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  CallToolRequest,
} from '@modelcontextprotocol/sdk/types.js';
import { ApiClient } from '../api/client.js';

export class CursorRulesMcpServer {
  private server: Server;
  private apiClient: ApiClient;

  constructor(baseUrl?: string) {
    this.log(`Initializing Agent Engineering Handbook MCP Server with baseUrl: ${baseUrl || 'default'}`);

    this.server = new Server(
      {
        name: 'cursor-engineering-rules-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.apiClient = new ApiClient(baseUrl);
    this.setupToolHandlers();
    this.log('Initialization complete');
  }

  private log(message: string) {
    const timestamp = new Date().toISOString();
    console.error(`${timestamp} [MCP Server] ${message}`);
  }

  private setupToolHandlers() {
    this.log('Setting up tool handlers...');

    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      this.log('ListTools request received');
      const tools = {
        tools: [
          {
            name: 'fetch_workflow_guide',
            description: 'Fetch the core workflow guide (Plan/Implement/Review with Golden Rules). Essential reading for all AI agents.',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
          {
            name: 'fetch_rule',
            description: 'Fetch a specific engineering rule (e.g., Python, Terraform, AWS, Kubernetes)',
            inputSchema: {
              type: 'object',
              properties: {
                category: {
                  type: 'string',
                  description: 'Category of the rule',
                  enum: ['core', 'languages', 'infrastructure', 'cloud', 'devops', 'patterns', 'databases', 'other'],
                },
                topic: {
                  type: 'string',
                  description: 'Specific topic (e.g., python, terraform, aws, kubernetes, docker)',
                },
              },
              required: ['category', 'topic'],
            },
          },
          {
            name: 'list_available_rules',
            description: 'List all available engineering rules with categories, descriptions, and priorities',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
        ],
      };
      this.log(`Returning ${tools.tools.length} available tools`);
      return tools;
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
      const { name, arguments: args } = request.params;
      this.log(`Tool called: "${name}" with args: ${JSON.stringify(args)}`);

      try {
        switch (name) {
          case 'fetch_workflow_guide': {
            this.log('Fetching workflow guide...');
            const startTime = Date.now();
            const rule = await this.apiClient.fetchMainGuide();
            const duration = Date.now() - startTime;
            this.log(`Workflow guide fetched successfully in ${duration}ms (${rule.content.length} chars)`);

            return {
              content: [
                {
                  type: 'text',
                  text: `# ${rule.title}\n\n${rule.description}\n\n---\n\n${rule.content}`,
                },
              ],
            };
          }

          case 'fetch_rule': {
            const { category, topic } = args as { category: string; topic: string };
            this.log(`Fetching rule: category="${category}", topic="${topic}"`);
            const startTime = Date.now();
            const rule = await this.apiClient.fetchRule(category, topic);
            const duration = Date.now() - startTime;
            this.log(`Rule fetched successfully in ${duration}ms (${rule.content.length} chars)`);

            return {
              content: [
                {
                  type: 'text',
                  text: `# ${rule.title}\n\n${rule.description}\n\nPriority: ${rule.priority}\n\n---\n\n${rule.content}`,
                },
              ],
            };
          }

          case 'list_available_rules': {
            this.log('Listing available rules...');
            const startTime = Date.now();
            const rules = await this.apiClient.listAvailableRules();
            const duration = Date.now() - startTime;
            this.log(`Available rules listed successfully in ${duration}ms (${rules.length} rules found)`);

            // Group by category
            const rulesByCategory = rules.reduce((acc, rule) => {
              if (!acc[rule.category]) {
                acc[rule.category] = [];
              }
              acc[rule.category].push(rule);
              return acc;
            }, {} as Record<string, typeof rules>);

            let text = '# Agent Engineering Handbook\n\n';
            text += 'Production-grade AI agent rules for 15+ languages, multi-cloud infrastructure, and DevOps.\n\n';
            text += '**Total Rules:** ' + rules.length + '\n\n';
            text += '---\n\n';

            for (const [category, categoryRules] of Object.entries(rulesByCategory)) {
              text += `## ${category.charAt(0).toUpperCase() + category.slice(1)}\n\n`;

              // Sort by priority
              const sorted = categoryRules.sort((a, b) => a.priority - b.priority);

              for (const rule of sorted) {
                text += `- **${rule.topic}** (priority: ${rule.priority}): ${rule.description}\n`;
              }
              text += '\n';
            }

            text += '---\n\n';
            text += '**Usage:** Call `fetch_rule` with category and topic to get the full rule content.\n';
            text += '**Example:** `fetch_rule(category="languages", topic="python")`\n';

            return {
              content: [
                {
                  type: 'text',
                  text,
                },
              ],
            };
          }

          default:
            this.log(`Unknown tool requested: "${name}"`);
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        this.log(`Tool execution failed for "${name}": ${errorMessage}`);
        throw new Error(`Tool execution failed: ${errorMessage}`);
      }
    });

    this.log('Tool handlers setup complete');
  }

  async start() {
    const transport = new StdioServerTransport();
    this.log('Agent Engineering Handbook MCP Server starting on stdio transport...');
    await this.server.connect(transport);
    this.log('Server connected and ready for requests');
  }

  getServer() {
    return this.server;
  }
}
