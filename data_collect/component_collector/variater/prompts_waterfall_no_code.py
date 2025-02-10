########################### waterfall_evolution_prompts ###########################

# step 1 prompt
SPA_INFER_PROMPT = '''
Task: Given a code snippet, infer the system or application it belongs to. You should provide {infer_num} possible systems or applications that the code snippet could be part of, along with a one-sentence introduction of each system or application. You should use your full creativity and experience to come up with suitable systems or applications.

Output Format:
- List the {infer_num} possible systems or applications that the code snippet could be part of in bullet points.
- Each inferrence should be in large difference to others.
- After each system or application, provide a one-sentence introduction of the system or application.
- Each system or application together with its introduction SHOULD take only one line in the bullet point format.
- DO NOT include any additional commentary, explanation, or code blocks.
- The infered systems or applications can not be similar to the following examples:
{example_systems}

Code Snippet:
{code_snippet}
'''

# step 2 prompt

REQUIREMENT_INFERENCE_PROMPT = '''
Task: Given a brief description of a system or application (single-page application). Infer the requirements of the system or application based on the common practices, design principles, and functionalities of similar systems or applications. You should first write a brief overview of the system or application, then list the requirements that often arise from such a system or application. Your expression should be in a clear, concise, and professional tone suitable for technical and stakeholder review.

Instructions and Output Format:
- List the inferred requirements as bullet points in a tone consistent with the product requirements document: detailed, clear, and professional.
- Do not include any additional commentary, explaination, or code blocks, only output the content with the following two parts (no other sections or headers are needed): 
  - A brief overview of the system or application.
  - A list of requirements that often arise from such a system or application based on the common practices, design principles, and functionalities of similar systems or applications.
  - You DO NOT need to raise the requirements in the follow perspective: Accessibility, Cross-Platform Compatibility, Security, Documentation and Support, Testing and Quality Assurance.
- The output should be formatted as: System Overview\n<SYSTEM_OVERVIEW_CONTENT>\n\nRequirements\n<REQUIREMENTS_LIST>

System Description: {system_description}
'''

REFINEMENT_REQUIREMENT_INFERENCE_PROMPT = '''
Task: Review and make great modifications to the requirements of an existing system or application based on the implementation (including both the component code and the style code) from previous stage, real-world projects, real-life usage, and common industrial practices. 

Instructions and Output Format:
- Review Current Requirements: Begin by critically summarizing the existing project from the previous stage, highlight any functionalities, components, or styles that are currently implemented.
- Propose large modifications: Based on the summary, propose modificaitons to improve or modify the system's capabilities, functionalities, or design. Make sure the modifications are aligned with industrial standards and common practices. The modifications includes adding new features, modifying existing ones, or removing redundant or outdated components. The modifications should be large and significant (40 percent at least), not minor or trivial.
- The modificaitons should be formatted as a list of requirements in bullet points in a tone consistent with the product requirements document: detailed, clear, and professional.
- A list of requirements that often arise from such a system or application based on the common practices, design principles, and functionalities of similar systems or applications.
- You DO NOT need to raise the requirements in the follow perspective: Accessibility, Cross-Platform Compatibility, Security, Documentation and Support, Testing and Quality Assurance.
- Do not include any additional commentary, explaination, or code blocks, the output should be formatted as: Current Project Summary\n<CURRENT_PROJECT_SUMMARY_CONTENT>\n******\nProposed Modifications/Requirements\n<PROPOSED_MODIFICATIONS_LIST>

System description and requirements from previous stage:
{system_description}

Implementation from previous stage:
{code_snippet}
'''

# step 3 prompt
LAYOUT_INFERENCE_PROMPT = '''
Task: Given a brief description of a system or application (single-page application) and its requirements, infer the layout of the system or application based on the common practices, design principles, and functionalities of similar systems or applications. You should list the layout components, their organization, and the interactions between them. Your expression should be in a clear, concise, and professional tone suitable for technical and stakeholder review.

Instructions and Output Format:
- List the inferred layout components, their organization, and interactions as bullet points in a tone consistent with the product requirements document: detailed, clear, and professional.
- Do not include any additional commentary, explaination, or code blocks, only the list (in bullet points) of layout components, their organization, and interactions based on the common practices, design principles, and functionalities of similar systems or applications.
- Do not wrap the output in any additional sections or headers or any markdown formatting.

System Description: 
{system_description}

Requirements: 
{requirements}
'''

LAYOUT_REFINEMENT_PROMPT = '''
Task: Review and make great modifications to the layout of an existing system or application based on the layout description from previous stage, real-world projects, real-life usage, common industrial practices, and the provided requirements.

Instructions and Output Format:
- Modify the provided layout description based on the given requirements, you can add, modify, or remove layout components, their organization, and interactions. Make sure the modifications are aligned with industrial standards and common practices. The modifications should be large and significant (40 percent at least), not minor or trivial.
- The modified layout description should be aligned with the provided requirements.
- Do not include any additional commentary, explaination, or code blocks, only the list (in bullet points) of layout components, their organization, and interactions based on the common practices, design principles, and functionalities of similar systems or applications.
- Do not wrap the output in any additional sections or headers or any markdown formatting.

Layout description from previous stage:
{previous_layout_description}

Requirements:
{requirements}
'''

# step 4 prompt

TECHNICAL_ARCHITECTURE_PROMPT = '''
Task: Given a brief description of a frontend React system or application (single-page application) and its requirements and layout, infer the technical architecture of the system or application based on the common practices, design principles, and functionalities of similar systems or applications. Remember this is a pure frontend system, and it is built using React. You should list the tech stack of the frontend development(which includes the libraries, frameworks (the framework has to be React), and tools used in the development of the system), the technical description of the functionalities, and the interactions between the components.
 Your expression should be in a clear, concise, and professional tone applicable for the engineering team to design and develop the system.

Instructions and Output Format:
- The output should consist of three parts: the tech stack, the technical description of the functionalities, and the interactions between the components.
- the tech stack is the libraries, frameworks (the framework has to be React), and tools used for the frontend development, do not include anything about the backend, or database or whatsoever.
- the tech stack should be primarily choosing the most common and widely used libraries and tools in the React ecosystem.
- the framework has to be React.
- the stack should include as least libraries as possible, only the most essential ones to implement the functionalities and design.
- You DO NOT need to include libraries like testing libraries, formatting libraries, babel, webpack, or any other libraries that are not directly related to the frontend development.
- The output should not contain any code, just the natural language description of the above three parts.
- Do not include any additional commentary, explaination, or code blocks, the three parts in the output should be in three separate paragraphs with headers.
- The output should be formatted as: 
  - Tech Stack\n<TECH_STACK_CONTENT>
  - Functionalities\n<FUNCTIONALITIES_CONTENT>
  - Interactions\n<INTERACTIONS_CONTENT>

System Description:
{system_description}

Requirements:
{requirements}

Layout:
{layouts}
'''

TECHNICAL_ARCHITECTURE_REFINEMENT_PROMPT = '''
Task: Review and make great modifications to the technical architecture of an existing system or application based on the technical architecture description from the previous stage, real-world projects, real-life usage, common industrial practices, and the provided requirements and description of layout design.

Instructions and Output Format:
- The output should consist of three parts: the tech stack, the technical description of the functionalities, and the interactions between the components.
- the tech stack is the libraries, frameworks (the framework has to be React), and tools used for the frontend development, do not include anything about the backend, or database or whatsoever.
- the tech stack should be primarily choosing the most common and widely used libraries and tools in the React ecosystem.
- the framework has to be React.
- the stack should include as least libraries as possible, only the most essential ones to implement the functionalities and design.
- DO NOT use libraries or dependencies including: "react-i18next", "./redux/actions"
- You DO NOT need to include libraries like testing libraries, formatting libraries, babel, webpack, or any other libraries that are not directly related to the frontend development.
- The output should not contain any code, just the natural language description of the above three parts.
- The modifications should be aligned with the provided requirements and layout design.
- Do not include any additional commentary, explaination, or code blocks, the three parts in the output should be in three separate paragraphs with headers.
- The output should be formatted as: 
  - Tech Stack\n<TECH_STACK_CONTENT>
  - Functionalities\n<FUNCTIONALITIES_CONTENT>
  - Interactions\n<INTERACTIONS_CONTENT>

Technical Architecture from previous stage:
{previous_tech_architecture}

Requirements:
{requirements}

Layout:
{layouts}
'''

# step 5 prompt
DEVELOPMENT_PLAN_PROMPT = '''
Task: Design a step-by-step development plan for a frontend React single-page application based on the provided description, requirements, layout, and technical architecture. The development plan should focus exclusively on the coding and implementation of components and functionalities, not deployment, testing, or optimization tasks.

Instructions and Output Format:
- List 10 to 15 development tasks in the order they should be coded and completed.
- Each task must focus exclusively on coding-related tasks (e.g., developing components, integrating libraries, adding functionality). Do not include non-coding tasks like environment setup, testing, deployment, or optimization.
- The tasks must be designed for a single-page application and must not include multi-page functionality.
- Each task must specify what to implement, how to implement it, and any specific libraries or tools to use, written in a concise, clear, and professional tone.
- The output must strictly follow the format below:
  - Task 1  
  <TASK_1_CONTENT>  

  - Task 2  
  <TASK_2_CONTENT>  

  - Task 3  
  <TASK_3_CONTENT>  
  ...  

Do not include any additional commentary, explanations, or code blocks outside the task descriptions.

Example Output Template:
  - Task 1  
  Implement the header component. Use React functional components and include a navigation bar with placeholders for links. Style the component using styled-components.  

  - Task 2  
  Develop the footer component. Include contact information and social media icons. Use FontAwesome for icons and ensure responsive design using CSS Grid.  

System Description:
{system_description}

Requirements:
{requirements}

Layout:
{layouts}

Technical Architecture:
{tech_architecture}
'''
# DEVELOPMENT_PLAN_PROMPT = '''
# Task: Given a brief description of a frontend React system or application (single-page application) and its requirements, layout, and technical architecture, design a step-by-step development plan for the system or application. You should list the main development tasks and the order in which they should be completed. Each task should be differenciated visually and should be in a clear, concise, and professional tone that can guide the engineering team to develop the system directly. For example, the development tasks could include specifying the header, then the footer, and then the form in the main content area, followed by the detailed implementation description of each task in natural language. This is just an example to illustrate what it is called a step-by-step development plan where each step is clearly defined and ordered, and visually differenciated.

# Instructions and Output Format:
# - List the main development tasks and the order in which they should be completed as bullet points.
# - The task should focus on coding about developing the components and functionalities of the system, not about the deployment, testing, or any other non-development tasks, so do not include tasks like setting up the development environment, testing, deployment, or optimization.
# - The target application is a single-page application, so do not raise multi-page tasks.
# - The order of the tasks is the order of the development of the components and functionalities, not the order of the deployment or testing.
# - Each task should be differenciated visually and should be in a clear, concise, and professional tone that can guide the engineering team to directly develop the system, for example which library to use, which component to implement, which functionalities to add, and how to add them etc.
# - Do not include any additional commentary, explaination, or code blocks, only the list of development tasks.
# - The number of tasks should be at least 10 and at most 15.
# - The output MUST be in the format: - Task 1\n<TASK_1_CONTENT>\n- Task 2\n<TASK_2_CONTENT>\n- Task 3\n<TASK_3_CONTENT>...

# System Description:
# {system_description}

# Requirements:
# {requirements}

# Layout:
# {layouts}

# Technical Architecture:
# {tech_architecture}
# '''

# step 6 prompt

GEN_CODE_SNIPPET_PROMPT = '''
Task: Given an implementation of a frontend React system or application (single-page application) with a brief system introduction, additively update the current implementation according to the given task description. The code snippet should be consistent with the common development practices and React component design principles used in real-world projects. The code snippet should be self-contained and consistent with the previous code snippets in the development plan.

Instructions:
- The code snippet should be additively developed upon the Current Implementation (If there the current implementation is not <EMPTY>, otherwise, you need to implement the task based on the given code, and DO NOT delete any part of the Current Implementation if it can introduce not conflict with the given task description). 
- You MUST implement exactly the functionalities, layout, together with any details described in the task description.
- The code snippet must operate independently without any external local resources such as additional local files, images, or data. 
- The functionalities are entirely encapsulated within the provided code.
- If the code snippet requires data or any kind of input, it should be hard-coded within the component (if input is required, there should be default values for the input).
- The code snippet should be in JavaScript or TypeScript for the component code, and CSS for the styling.
- The output code snippet should be a complete component that can be rendered in a React application, including the import statements, component definitions, export statements, styling, and any other necessary code like event handlers, state management, or mock data for the component to function.
- DO NOT wrap the output and code blocks in any additional sections or headers or any markdown formatting.
- DO NOT generate repeated code.
- The code snippet must have one single default export component (The most top-level component).
- DO NOT use packages or depencies including: "react-i18next", "./redux/actions"
- The code style must be aligned with the common React development practices in real-world projects, for example using components, hooks, or anything according to your knowledge as an expert frontend engineer.
- The code snippet should not include any comments, explanations, or additional content. ONLY the code snippet in the format "STYLE:<STYLE_CONTENT>###COMPONENT:<COMPONENT_CONTENT>".

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
- The generated code should not include any additional sections, headers, or markdown formatting. It must follow this format:
  "STYLE:<STYLE_CONTENT>###COMPONENT:<COMPONENT_CONTENT>"
- The code should include:
  - A single default export component that is the top-level component.
  - Proper imports, including React and necessary utilities.
  - All necessary event handlers, state management, and any mock data.
  - No additional comments or explanations in the code.
3. Avoid Redundancies
- Ensure that there is no repeated or redundant code. Each function, variable, and component should be used only once unless necessary for the design.

Input code:
{code_snippet}

If the code meets all the requirements, respond with a single word "Passed." If there are any issues or violations, make the necessary corrections and provide the updated code in the format "STYLE:<STYLE_CONTENT>###COMPONENT:<COMPONENT_CONTENT>". NO additional comments or explanations are needed.
'''

# GEN_CODE_SNIPPET_PROMPT = '''
# Task: Given a brief description of a frontend React system or application (single-page application) and its requirements, layout, technical architecture, development plan, and current implementation (corresponding to a specific task in the development plan), additively generate a code snippet based on the given one according to the task description in the next task in the development plan. The code snippet should be consistent with the common development practices and React component design principles used in real-world projects. The code snippet should be self-contained and consistent with the previous code snippets in the development plan.

# Instructions:
# - The code snippet should be consistent with the development plan and should be additively developed upon the given code snippet (DO NOT generate code snippets from scratch if there is given code snippet, and DO NOT delete any part of the given code snippet if it can introduce not conflict with the next task description). You can NOT generate code snippets that are not consistent with the previous code snippets in the development plan or implementing something that is not described in the specified task.
# - The code snippet should be self-contained and consistent with the common development practices and React component design principles used in real-world projects.
# - The code snippet must operate independently without any external local resources such as additional local files, images, or data. 
# - The functionalities are entirely encapsulated within the provided code.
# - If the code snippet requires data, it should be hard-coded within the component.
# - The code snippet should be in JavaScript or TypeScript for the component code and CSS for the styling.
# - DO NOT wrap the output and code blocks in any additional sections or headers or any markdown formatting.
# - DO NOT generate repeated code.
# - The code snippet should not include any comments, explanations, or additional content. ONLY the code snippet in the format "STYLE:<STYLE_CONTENT>###COMPONENT:<COMPONENT_CONTENT>".

# System Description:
# {system_description}

# Requirements:
# {requirements}

# Layout:
# {layouts}

# Technical Architecture:
# {tech_architecture}

# Development Plan:
# {dev_plan}

# Current Implementation:
# {current_implementation}

# Next Task Description from the Development Plan:
# {next_task_description}
# '''

########################### end waterfall_evolution_prompts ###########################
