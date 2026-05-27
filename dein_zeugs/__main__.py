import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    from dein_zeugs.cli import main
    main()
