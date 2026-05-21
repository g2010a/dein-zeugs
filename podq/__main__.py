import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    from podq.cli import main
    main()
