def add_default_args(parser):
    """This adds default command_line arguments for all Yoda-clienttools
       to the command-line argument parser."""
    parser.add_argument("-y", "--yoda-version", default=None,
                        choices=["1.8", "1.9", "1.10", "2.0"],
                        help="Override Yoda version on the server")
