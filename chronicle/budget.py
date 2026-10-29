"""Budget CLI outside guard's eager imports, avoiding the runpy import warning."""

from chronicle.guard.remote_budget import main

if __name__ == "__main__":
    main()
