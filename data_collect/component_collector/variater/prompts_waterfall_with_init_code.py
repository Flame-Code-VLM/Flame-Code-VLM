########################### waterfall_evolution_prompts ###########################

# step 1 prompt
SPA_INFER_PROMPT = '''
Given a React code snippet that I want to integrate into a larger, real-world, production-grade, single-page frontend system. Your task is to propose exactly {infer_num} distinct, fully-featured production-ready frontend React systems where this code snippet can play a meaningful role. Each system should be self-contained, modular, and entirely client-side with no dependencies on backend APIs or real-time data sources.

Each proposed system must be a real, useful product or tool that could exist in a commercial, industrial, or enterprise context. The system should feel like something that could be released as a standalone product (like a SaaS tool, utility app, or data visualization tool) and not a "demo" project.

Proposal Requirements
1. System Name: Provide a name for the system.
2. System Category/Type: Identify the type of system (e.g., interactive dashboard, design tool, productivity app, data visualization app, etc.).
3. System Purpose and Use Case: Describe the purpose of the system, its primary function, and what real-world problem it solves.
4. How the Provided Code Snippet Fits: Clearly explain how and where the provided React code snippet would be used as a key part of the system (e.g., as a core component, widget, or logic handler).
5. System Complexity: Each system must include at least 3-4 interconnected components or sub-modules (not pages) that logically interact with each other.
6. Core Features: Each system should have at least 5-7 essential production-grade features. Example features include:
  - Data visualization and graphs (e.g., charts, dashboards)
  - Interactive forms and filters (e.g., dynamic search, multi-step form validation)
  - Dynamic UI updates (without real-time data — instead, use hardcoded, local JSON or JavaScript objects as data)
  - Stateful UI logic (e.g., tabs, modals, tooltips, or collapsible views)
  - Interactive elements (e.g., drag-and-drop, sliders, sortable lists, or resizable panels)
  - Responsive design (ensure responsiveness across desktop, tablet, and mobile)

Important Guidelines:
- The systems must be built as self-contained, single-page applications. Avoid multiple pages, page reloads, or navigation logic (like "404 pages" or "about pages").
- The system must feel like a standalone product that could be used by a business or an individual. It should not be a "demo" project.
- Each system should use mocked local data (e.g., hard-coded JSON, JavaScript arrays, or default props) for any data-driven features. No real-time data or backend API calls should be used.
- Each system should have distinct logic, purpose, and design. For example, a "To-Do List" app and a "Task Planner" are too similar.
- The output MUST only contain the proposed systems in the following JSON format (you MUST NOT change the key names or add any additional content):
  [
    {{
      "name": "System Name",
      "category": "System Category",
      "purpose": "System Purpose and Use Case",
      "code_snippet_usage": "How the Provided Code Snippet Fits",
      "complexity": "System Complexity",
      "features": "Core Features"
    }},
    {{
      "name": "System Name",
      "category": "System Category",
      "purpose": "System Purpose and Use Case",
      "code_snippet_usage": "How the Provided Code Snippet Fits",
      "complexity": "System Complexity",
      "features": "Core Features"
    }},
    ...
  ]
  NO other comments, explainations, or any content is needed, and do not wrap with markdown.

- The infered systems or applications can not be similar to the following examples:
{example_systems}

Code Snippet:
{code_snippet}
'''

# step 2 prompt
DEVELOPMENT_PLAN_PROMPT = '''
Given a description of a pure frontend system/application, create a complete, step-by-step development roadmap for building this system from start to finish. The development process should follow an additive approach, meaning each step builds on the previous one, introducing new logic, components, and interactive features. The goal is to create a fully-functional, production-grade, standalone React application.

Development Plan Requirements
1. General Structure
  - The system should be developed over at least 15-20 development steps to ensure sufficient complexity and production-grade features.
  - Each step should be large enough to feel like a deliverable milestone, and there MUST be some changes on the visual outlook as well(for example adding/removing/updating components or updating layouts). Each step should introduce significant system-level features, logic updates, or interactive functionality.
  - Each step must be self-contained and should culminate in a single, large, production-grade, single-file React application. This means that all components, styles, logic, and state must be written in one large self-contained code chunk (no imports from local files).
  - The updated should avoid invisible changes (e.g., only updating comments, minor code formatting, or the components can only be seen if some interactions are made).
  - No external data sources or real-time data can be used. If data is needed, it must be hardcoded in the component logic using JSON objects, JavaScript arrays, or mock data.
  - No file separation is allowed. All components, logic, and functionality must exist within a single large code block (one big self-contained React file).

2. Details for Each Step
  - Step Title: A clear name for the development task (e.g., "Build a Filterable Table", "Create a Dashboard with Sorting and Pagination").
  - Objective: The purpose of this step (e.g., "Enable users to sort the table columns dynamically").
  - Components/Logic Introduced: Specify which new logic, components, or features are introduced in this step.
  - How It Builds on the Previous Step: Explain how this step logically builds on the previous one (e.g., "Now that data is displayed, this step enables interactive filtering").
  - Best Practices: Indicate best practices being followed (e.g., "Use memoization to optimize render performance", "Use DRY principles to avoid repeating logic").

3. Example Development Process (3 steps for illustration)
  - Step 1
    Set Up Initial Layout and Component Structure
    Objective: Create the initial layout and component structure for the dashboard.
    Components/Logic Introduced:
      Create Header, Sidebar, and Main Content Area as self-contained elements in the code.
      Hardcode sample navigation items in the sidebar (like "Home", "Reports", "Settings").
      Create an empty Data Display Area where dynamic components (like charts or tables) will be rendered later.
    How It Builds on the Previous Step: Since this is the first step, it sets the foundation for later steps where logic, interactivity, and dynamic features will be added.
    Best Practices:
      Use reusable functions and self-contained components.
      Use Flexbox or CSS Grid to create a responsive layout.
  - Step 2
    Create a Data Table with Hardcoded Data
    Objective: Create a simple table component that displays hardcoded data.
    Components/Logic Introduced:
      Add a DataTable inside the Main Content Area.
      Use map() to iterate over hardcoded data and render each row dynamically.
      Add simple headers (like "Name", "Age", "Role", "Location").
    How It Builds on the Previous Step: The DataTable is displayed inside the Main Content Area created in Step 1.
    Best Practices:
      Pass data as a variable at the top of the file, not as an external file import.
      Use array map() to generate table rows dynamically.
  - Step 3
    Add Sorting Functionality to the Data Table
    Objective: Allow users to sort table columns by clicking on the headers (e.g., clicking "Age" sorts the table by age).
    Components/Logic Introduced:
      Add sort state to track the column being sorted and the sort order (ascending/descending).
      Modify the table headers so that clicking on them triggers the sort.
    How It Builds on the Previous Step: Builds on the existing DataTable by adding interactivity.
    Best Practices:
      Use React state to track sorting.
      Optimize sorting logic with React.memo.

4. Final Requirements for the Development Plan
  - Self-Contained Single-File Code: The final system, when fully implemented, should exist in a single, large React file. All components, logic, and styles must exist within this file. No imports of local files, CSS files, or additional components are allowed.
  - Hardcoded Data Only: If any data is required for the system, it must be stored directly in the file using hardcoded objects, arrays, or default values.
  - Single-Page Application (SPA): The system must not use any page-based navigation logic. All interactions should take place within the same page.
  - Fully Incremental Steps: The system should evolve naturally as each development task is completed, with each task adding significant logic or interactivity.
  - Complexity and Depth: Ensure the system has sufficient depth and complexity. It should have at least 15-20 development steps to demonstrate meaningful growth and progression.
  - The output MUST only contains the step list in the JSON format (you MUST NOT change the key names or add any additional content): 
    [
      {{
        "title": "Step Title",
        "objective": "Objective Description",
        "components_logic": "Components/Logic Introduced",
        "builds_on": "How It Builds on the Previous Step",
        "best_practices": "Best Practices Followed"
      }},
      {{
        "title": "Step Title",
        "objective": "Objective Description",
        "components_logic": "Components/Logic Introduced",
        "builds_on": "How It Builds on the Previous Step",
        "best_practices": "Best Practices Followed"
      }},
      ...
    ]
  no titles, headings, comments or any other content is needed, and do not wrap with markdown.

System Description:
{system_description}

Code Snippet:
{code_snippet}
'''

# step 6 prompt
GEN_CODE_SNIPPET_PROMPT_ITER = '''
Task: Given an implementation of a frontend React system or application (single-page application) with a brief system introduction, current development task and current implementation of the system. Additively update the current implementation according to the given task description. The generated code should be consistent with the common development practices and React component design principles used in real-world projects. The generated code should be self-contained. You should also learn the coding style and design patterns from the reference code as well, incorporate the similar implementation if the reference code matches the current task.

Instructions:
- The generated code should be additively developed upon the Current Implementation (you need to implement the task based on the Current Implementation, you MUST NOT start from scratch). 
- You MUST implement exactly the functionalities, layout, together with any details described in the task description.
- The generated code must operate independently without any external local resources such as additional local files, images, or data. 
- The functionalities are entirely encapsulated within the generated code.
- If the generated code requires data or any kind of input, it should be hard-coded within the component (if input is required, there should be default values for the input).
- The generated code should be in JavaScript or TypeScript for the component code, and CSS for the styling.
- The output generated code should be a complete component that can be rendered in a React application, including the import statements, component definitions, export statements, styling, and any other necessary code like event handlers, state management, or mock data for the component to function.
- DO NOT wrap the output and code blocks in any additional sections or headers or any markdown formatting.
- DO NOT generate repeated code.
- The generated code must have one single default export component (The most top-level component).
- DO NOT use packages or depencies including: "react-i18next", "./redux/actions"
- The code style must be aligned with the common React development practices in real-world projects, for example using components, hooks, or anything according to your knowledge as an expert frontend engineer.
- The style spcification must be implemented with the styled-components and no other CSS, SCSS, or LESS specifications are allowed.
- The generated code should not include any comments, explanations, or additional content. ONLY the generated code.

System Introduction:
{system_description}

Current Implementation:
{current_implementation}

Task Description:
{next_task_description}
'''

DOUBLE_CHECK_PROMPT = '''
Review the given code. Ensure the following requirements are met:

1. Self-Containment
- Ensure that the generated component operates independently without relying on external resources such as files, images, or external data (e.g., API calls). If the component requires any input data, it should be hardcoded (mocked) within the component itself, using default values wherever necessary.
- All dependencies must be included directly in the code (i.e., there should be no missing imports or external files).
2. Code Structure and Format
- The generated code should not include any additional sections, headers, or markdown formatting.
- The code should include:
  - A single default export component that is the top-level component.
  - Proper imports, including React and necessary utilities.
  - All necessary event handlers, state management, and any mock data.
  - No additional comments or explanations in the code.
3. Avoid Redundancies
- Ensure that there is no repeated or redundant code. Each function, variable, and component should be used only once unless necessary for the design.

Input code:
{code_snippet}

If the code meets all the requirements, respond with a single word "Passed." If there are any issues or violations, make the necessary corrections and answer with the updated code ONLY. NO additional comments or explanations are needed.
'''

########################### end waterfall_evolution_prompts ###########################
