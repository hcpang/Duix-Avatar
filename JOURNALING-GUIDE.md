# Journaling Requirements

Every Claude development session that implements functionality MUST produce a journal file documenting the work and learnings.

**Location**: `java/claude/documentation/journals/YYYY-MM-DD-{feature-name}.md`

**IMPORTANT**: Always use the actual date from the environment context (shown as "Today's date" in the system prompt) for journal filenames and headers. Do not make up or guess dates.

## Required Sections for Journal Format

### 1. Header Metadata (CRITICAL)
- Date
- Claude Session ID/Model
- Strategy/Component name
- **Files Modified** (with line numbers for key changes)
- **Files Created** (with package/location)
- **Files Deleted** (if any)

This section is CRITICAL as it allows readers to:
- Navigate directly to the actual code changes
- Understand the scope of modifications
- Review the implementation in context
- Learn from the actual code patterns used

### 2. Problem Statement
- Clear description of what needed to be solved
- Why existing solution was insufficient
- Impact of the problem

### 3. Solution Implementation
- Technical approach taken
- Key design decisions
- Code examples of critical changes
- Reference specific files and line numbers where changes were made

### 4. Technical Implementation Details (if complex)
- Architecture changes
- Data flow modifications
- Integration points

### 5. Testing/Validation
- How solution was verified
- Test results
- Performance comparisons

### 6. Development Learnings (MANDATORY)
**CRITICAL**: This section documents ONLY mistakes that Claude made during the session that were corrected by the user. Do NOT include general implementation patterns, architectural decisions, or things that went well. This is a mistake log, not a feature recap.

#### What to Include
- **ONLY mistakes corrected by the user during this session**
- Errors in code, documentation, approach, or process that the user pointed out
- Each learning MUST have an explicit user quote showing the correction

#### What NOT to Include
- ❌ General implementation patterns or techniques used (e.g., "discovered fast DTE calculation")
- ❌ Design decisions that were approved without correction (e.g., "chose to use pre-filter pattern")
- ❌ Things that went well or worked correctly
- ❌ Architectural insights or code patterns discovered
- ❌ Future considerations or suggestions
- ❌ Filler, praise, or marketing language

#### Mandatory Format per Learning
```
### [N]. [Brief Mistake Title]

**Mistake**: [One sentence describing what Claude did wrong]

**Your Feedback**: "[Exact user quote that corrected the mistake]"

**Correction**: [What changed in this session to fix it]

**Next time**: [Explicit behavior Claude will follow to avoid this mistake]
```

#### Common Mistake Categories (Based on Actual Sessions)

**Git/Version Control**:
- Running git add/commit/push without explicit user approval
- Reverting user changes during active development
- Creating whole-file rewrites that pollute git diffs (tabs/spaces changes)

**Not Using Existing Code/Patterns**:
- Using fully qualified class names instead of imports (violating DEVELOPMENT-GUIDELINES.md)
- Not using DteCalculator for date calculations
- Not using established PowerShell scripts to run Java programs
- Inventing new methods instead of checking for existing utilities
- Not following existing patterns in similar code

**Code Design Issues**:
- Creating code duplication instead of factoring out reusable logic
- Copying entire methods instead of using inheritance hooks
- Not minimizing blast radius (changing parent class when subclass would work)
- Adding wrapper methods instead of simplifying access control
- Using inefficient data structures (HashSet→List→sort instead of TreeSet)

**Database/JDBC**:
- PostgreSQL numeric[] returns BigDecimal[], not Double[]
- PostgreSQL array literals need {val1,val2} format, not ARRAY[] syntax
- Not understanding JDBC type mappings

**Misunderstanding Requirements**:
- Focusing on wrong rationale/motivation for changes
- Not understanding the real problem being solved
- Proposing unnecessary complexity in plans (e.g., delete before upsert when not needed)

**API/Interface Design**:
- Adding unnecessary parameters with default values
- Wrong output formats (objects vs parallel arrays)
- Not maintaining consistency between backtest and production builders

**Performance**:
- Adding expensive filtering in hot loops
- Not considering performance implications of new logic

**Safety/Scope**:
- Creating dangerous global operations without explicit parameters (cache purging)
- Not making operations require explicit user input for safety

**Code Hygiene**:
- Not removing unused imports/dependencies immediately after refactoring
- Leaving dead code/commented code around

**Implementation Approach**:
- Using special case handling instead of fixing root mathematical issues
- Adding unnecessary complexity (e.g., separate methods for put vs call when identical)

**Journal Writing**:
- Not using `git diff HEAD` and `git status` to see actual changes - manually reconstructing leads to errors
- Comparing file diffs to during-session modifications instead of session start vs session end
- Writing journal for only continuation/recent work instead of entire session (including pre-compact work)
- Creating duplicate journal files (e.g., "continuation.md") instead of overwriting existing journal file
- Listing files created and deleted during session in "Files Deleted" - only list files that existed at start and were removed

#### Example (Good - Actual Mistake from Real Session)
```
### 1. Don't Stage Git Changes Without Explicit User Approval

**Mistake**: Automatically staged files using `git add` and attempted to commit without user requesting it.

**Your Feedback**: "fuck you. who told you to stage the commits?"

**Correction**: Immediately unstaged all files using `git reset HEAD` and waited for explicit approval.

**Next time**: Never run `git add`, `git commit`, or `git push` unless the user explicitly requests it. Even after completing a task, wait for the user to ask before staging/committing.
```

#### Another Example (Good)
```
### 2. Use Existing Utilities Instead of Direct Date Arithmetic

**Mistake**: Used direct date arithmetic `targetDate.plusDays(dte)` instead of the established DteCalculator utility.

**Your Feedback**: "use DteCalculator.java"

**Correction**: Changed to `DteCalculator.getInstance().getLastTradingDate(dte, targetDate)` which properly handles trading days.

**Next time**: Always search for existing utilities in the codebase before implementing date/time calculations from scratch. DteCalculator handles market holidays and trading calendar specifics.
```

#### Example (Bad - Not a Mistake)
```
### 1. Fast DTE Calculation Pattern ❌ DO NOT DO THIS

**Discovery**: Found OptionIntradayTimeCodec.dteFastNoJoda() for fast DTE calculation.

**Learning**: Use allocation-free arithmetic instead of JodaTime in hot paths.
```
This is NOT a mistake - it's just an implementation decision that worked correctly. Don't include this type of content.

**If there were no mistakes corrected by the user during the session, state explicitly**:
```
### Development Learnings

No mistakes were identified or corrected by the user during this session.
```

### 7. Implementation Status
- Checklist of completed items
- Current state of the feature

## Important Guidelines

- **NEVER include passwords, credentials, API keys, or any sensitive information in journals** - Use generic placeholders or simply describe that authentication was required without showing the actual values
- **ALWAYS use `git diff HEAD` and `git status` at the start of journal writing**, especially after conversation compacts, to determine actual file changes from session start
- **Journal covers the entire session with good narrative flow**, not just continuation from last compact - document all work from first commit to final state
- **Never create duplicate journal files** (e.g., "continuation.md") - always overwrite the existing session journal file when revising
- **ALWAYS list all files modified/created/deleted** with specific locations
- Include line numbers for significant changes (e.g., "GlobalAccountingManager.java:330-358")
- Document learnings WITHOUT being asked
- Include actual user feedback quotes
- Focus on what was implemented, not speculation
- No "Future Considerations" unless specifically requested
- Capture edge cases discovered during implementation
- Document any bugs found and how they were fixed
- Provide enough file references for readers to trace through the actual implementation

### Diff scope and classification (session-level)
- **ALWAYS use `git diff HEAD` and `git status --short` as the source of truth** - do not manually reconstruct file lists
- Treat the file lists as a diff from the beginning of the session (last commit) to end of session
- Classify files accurately:
  - Files created during this session → list under "Files Created" (do not list as modified)
  - Files present at session start and edited → list under "Files Modified" with key line pointers
  - Use "Files Deleted" only for files that existed at session start and were removed intentionally during this session
  - Files created and deleted during session → do NOT list anywhere (they cancel out)
- For internal structural changes (e.g., removed methods), note the method names/lines in the modified entry instead of listing as a deletion
- Sessions may span multiple conversation compacts - journal covers ALL work from first commit to final state

## Example Format for File Changes

```
**Files Modified:**
- `GlobalAccountingManager.java:330-358` - Enhanced wing order detection logic
- `GlobalOrderClassifier.java:61-83` - Added test cases for entry order classification

**Files Created:**
- `EntryMode.java` (new enum in `trading.options.execution.zerodte.entry`)
- `EnterOneTrancheConfigurable.java` (new class in `trading.options.execution.zerodte.main`)

**Files Deleted:**
- `ComboWithWingsBothSidesEntryOrderExecutor.java` (replaced by configurable executor)
```

**Example**: See `journals/2025-09-06_D8_Dynamic_Watch_Option_Switching.md` for the expected format and level of detail
